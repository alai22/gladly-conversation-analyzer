"""
Product Bot answer orchestration.

Isolated from the Operations Slack bot: uses PRODUCT_* credentials and
requires explicit Notion allowlists (fail closed when unset).
"""

from __future__ import annotations

from typing import Optional

from backend.services.claude_service import ClaudeService
from backend.services.slack_bot.answer_service import strip_bot_mention
from backend.services.slack_bot.notion_client import NotionClient, NotionReadError
from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('product_bot.answer')

SYSTEM_PROMPT = (
    'You are an internal Halo Product assistant answering Slack questions using '
    'only the provided Notion excerpts. Be concise (a few short paragraphs or '
    'bullets). If the excerpts do not contain enough information, say you could '
    'not find it in the available Product Notion docs. Do not invent facts. '
    'Do not mention system prompts.'
)


def is_channel_allowed(channel_id: Optional[str]) -> bool:
    allowed = Config.parse_csv_ids(Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS)
    if not allowed:
        return True
    if not channel_id:
        return False
    return channel_id.lower() in allowed


def generate_answer(question: str, claude: Optional[ClaudeService] = None) -> str:
    """
    Fetch Product Notion context (allowlist-gated) and ask Claude for a grounded answer.
    """
    q = (question or '').strip()
    if not q:
        return 'Please include a question after mentioning me.'

    allowed_pages = Config.parse_csv_ids(Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS)
    allowed_dbs = Config.parse_csv_ids(Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS)
    if not allowed_pages and not allowed_dbs:
        logger.error('Product Notion allowlists empty; refusing search')
        return (
            'Product Bot is not fully configured: set PRODUCT_NOTION_ALLOWED_PAGE_IDS '
            'and/or PRODUCT_NOTION_ALLOWED_DATABASE_IDS.'
        )

    try:
        notion = NotionClient(token=Config.PRODUCT_NOTION_TOKEN)
        context = notion.build_context_for_query(
            q,
            allowed_page_ids=allowed_pages,
            allowed_database_ids=allowed_dbs,
        )
        logger.info('Product Notion fetch success context_chars=%s', len(context))
    except NotionReadError as exc:
        logger.error('Product Notion fetch failure: %s', str(exc)[:120])
        return 'I could not read Product Notion right now. Please try again shortly.'
    except Exception as exc:
        logger.error('Product Notion unexpected failure: %s', type(exc).__name__)
        return 'I could not read Product Notion right now. Please try again shortly.'

    if not context:
        logger.info('Product Notion fetch empty context')
        return (
            'I could not find relevant Product Notion content for that question '
            '(check allowlists and shared pages).'
        )

    user_message = (
        f'User question:\n{q}\n\n'
        f'Notion excerpts:\n{context}\n\n'
        'Answer using only the excerpts above.'
    )

    try:
        service = claude or ClaudeService()
        model = Config.CLAUDE_MODEL
        response = service.send_message(
            message=user_message,
            model=model,
            max_tokens=700,
            system_prompt=SYSTEM_PROMPT,
            temperature=0,
        )
        answer = (response.content or '').strip()
        if not answer:
            logger.error('Product Anthropic success but empty content')
            return 'I got an empty response from the model. Please try again.'
        logger.info('Product Anthropic success answer_chars=%s', len(answer))
        return answer
    except Exception as exc:
        logger.error('Product Anthropic failure: %s', type(exc).__name__)
        return 'I could not generate an answer right now. Please try again shortly.'