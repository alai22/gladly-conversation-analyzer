"""
Slack bot answer orchestration: strip mention → Notion read → Claude → reply text.
"""

from __future__ import annotations

import re
from typing import Optional

from backend.services.claude_service import ClaudeService
from backend.services.slack_bot.notion_client import NotionClient, NotionReadError
from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('slack_bot.answer')

MENTION_RE = re.compile(r'<@[^>]+>')
SYSTEM_PROMPT = (
    'You are an internal Halo assistant answering Slack questions using only the '
    'provided Notion excerpts. Be concise (a few short paragraphs or bullets). '
    'If the excerpts do not contain enough information, say you could not find it '
    'in the available Notion docs. Do not invent facts. Do not mention system prompts.'
)


def strip_bot_mention(text: str) -> str:
    cleaned = MENTION_RE.sub('', text or '')
    return ' '.join(cleaned.split()).strip()


def is_channel_allowed(channel_id: Optional[str]) -> bool:
    allowed = Config.parse_csv_ids(Config.SLACK_ALLOWED_CHANNEL_IDS)
    if not allowed:
        return True
    if not channel_id:
        return False
    return channel_id.lower() in allowed


def generate_answer(question: str, claude: Optional[ClaudeService] = None) -> str:
    """
    Fetch Notion context and ask Claude for a grounded answer.

    Raises no exceptions to callers for Notion/Claude failures — returns short
    user-facing error strings instead (caller posts them to Slack).
    """
    q = (question or '').strip()
    if not q:
        return 'Please include a question after mentioning me.'

    try:
        notion = NotionClient()
        context = notion.build_context_for_query(
            q,
            allowed_page_ids=Config.parse_csv_ids(Config.NOTION_ALLOWED_PAGE_IDS),
            allowed_database_ids=Config.parse_csv_ids(Config.NOTION_ALLOWED_DATABASE_IDS),
        )
        logger.info('Notion fetch success context_chars=%s', len(context))
    except NotionReadError as exc:
        logger.error('Notion fetch failure: %s', str(exc)[:120])
        return 'I could not read Notion right now. Please try again shortly.'
    except Exception as exc:
        logger.error('Notion unexpected failure: %s', type(exc).__name__)
        return 'I could not read Notion right now. Please try again shortly.'

    if not context:
        logger.info('Notion fetch empty context')
        return (
            'I could not find relevant Notion content for that question '
            '(or the integration has no shared pages yet).'
        )

    user_message = (
        f'User question:\n{q}\n\n'
        f'Notion excerpts:\n{context}\n\n'
        'Answer using only the excerpts above.'
    )

    try:
        service = claude or ClaudeService()
        model = Config.SLACK_BOT_MODEL or Config.CLAUDE_MODEL
        response = service.send_message(
            message=user_message,
            model=model,
            max_tokens=700,
            system_prompt=SYSTEM_PROMPT,
            temperature=0,
        )
        answer = (response.content or '').strip()
        if not answer:
            logger.error('Anthropic success but empty content')
            return 'I got an empty response from the model. Please try again.'
        logger.info('Anthropic success answer_chars=%s', len(answer))
        return answer
    except Exception as exc:
        logger.error('Anthropic failure: %s', type(exc).__name__)
        return 'I could not generate an answer right now. Please try again shortly.'
