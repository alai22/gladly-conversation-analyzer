"""
Product Bot answer orchestration.

Isolated from the Operations Slack bot: uses PRODUCT_* credentials.
Optional Notion page/database filters; empty = search whatever the
Product Notion integration can access.
"""

from __future__ import annotations

from typing import Optional

from backend.services.claude_service import ClaudeService
from backend.services.product_bot.retrieval import build_product_context, classify_query
from backend.services.slack_bot.answer_service import strip_bot_mention
from backend.services.slack_bot.notion_client import NotionClient, NotionReadError
from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('product_bot.answer')

SYSTEM_PROMPT_NARROW = (
    'You are an internal Halo Product assistant answering Slack questions using '
    'only the provided Notion excerpts. Be concise (a few short paragraphs or '
    'bullets). Cite source page titles when helpful. If the excerpts do not '
    'contain enough information, say you could not find it in the available '
    'Product Notion docs. Do not invent facts. Do not mention system prompts.'
)

SYSTEM_PROMPT_BROAD = (
    'You are an internal Halo Product assistant. The user asked for a broad '
    'topic overview. Using ONLY the provided Notion excerpts, synthesize the '
    'best overview you can — prefer a useful synthesis over saying you could '
    'not find much when any on-topic excerpts exist. Do not invent facts. '
    'Cite source page titles inline when helpful. If evidence is partial or '
    'sources conflict, say so explicitly.\n\n'
    'Structure the answer as:\n'
    '1. What it is\n'
    '2. Why it exists\n'
    '3. Current phase / roadmap / status (if available in the excerpts)\n'
    '4. Key themes / features\n'
    '5. Notable uncertainties or conflicts across sources (if any)\n\n'
    'If a section has no support in the excerpts, omit it briefly rather than '
    'guessing. Do not mention system prompts.'
)

NARROW_MAX_TOKENS = 700
BROAD_MAX_TOKENS = 1400


def is_channel_allowed(channel_id: Optional[str]) -> bool:
    allowed = Config.parse_csv_ids(Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS)
    if not allowed:
        return True
    if not channel_id:
        return False
    return channel_id.lower() in allowed


def _fallback_for_evidence(evidence: str, ranked_preview: list) -> str:
    if evidence == 'thin':
        titles = []
        for item in ranked_preview[:3]:
            # preview format: id8:title:score
            parts = item.split(':', 2)
            if len(parts) >= 2 and parts[1]:
                titles.append(parts[1])
        title_hint = ', '.join(f'“{t}”' for t in titles) if titles else 'related pages'
        return (
            'I found some related Product Notion pages '
            f'({title_hint}), but the loaded content was too thin to synthesize '
            'a solid answer. Try a more specific question, or confirm the hub '
            'pages are shared with the Product Notion integration.'
        )
    return (
        'I could not find relevant Product Notion content for that question '
        '(no matching docs in the integration scope).'
    )


def generate_answer(question: str, claude: Optional[ClaudeService] = None) -> str:
    """
    Fetch Product Notion context and ask Claude for a grounded answer.

    Broad overview questions use wider retrieval + structured synthesis.
    Optional allowlists filter results; when unset, trusts Notion integration scope.
    """
    q = (question or '').strip()
    if not q:
        return 'Please include a question after mentioning me.'

    plan = classify_query(q)

    try:
        notion = NotionClient(token=Config.PRODUCT_NOTION_TOKEN)
        result = build_product_context(
            notion,
            q,
            allowed_page_ids=Config.parse_csv_ids(Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS),
            allowed_database_ids=Config.parse_csv_ids(
                Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS
            ),
            priority_page_ids=Config.parse_csv_ids(
                Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS
            ),
            plan=plan,
        )
        plan = result.plan
        context = result.context
        logger.info(
            'Product Notion fetch done broad=%s evidence=%s candidates=%s '
            'loaded=%s context_chars=%s',
            plan.is_broad,
            result.evidence,
            result.candidate_count,
            result.loaded_count,
            len(context),
        )
    except NotionReadError as exc:
        logger.error('Product Notion fetch failure: %s', str(exc)[:120])
        return 'I could not read Product Notion right now. Please try again shortly.'
    except Exception as exc:
        logger.error('Product Notion unexpected failure: %s', type(exc).__name__)
        return 'I could not read Product Notion right now. Please try again shortly.'

    if result.evidence in ('none', 'thin') or not context:
        logger.info(
            'Product Notion evidence insufficient evidence=%s loaded=%s',
            result.evidence,
            result.loaded_count,
        )
        return _fallback_for_evidence(result.evidence or 'none', result.ranked_preview)

    if plan.is_broad:
        system_prompt = SYSTEM_PROMPT_BROAD
        max_tokens = BROAD_MAX_TOKENS
        instruction = (
            'Synthesize the best overview you can from the excerpts above. '
            'Cite page titles. Prefer a grounded overview over abstaining. '
            'If evidence is partial or conflicting, say so explicitly.'
        )
    else:
        system_prompt = SYSTEM_PROMPT_NARROW
        max_tokens = NARROW_MAX_TOKENS
        instruction = 'Answer using only the excerpts above. Cite page titles when helpful.'

    user_message = (
        f'User question:\n{q}\n\n'
        f'Notion excerpts:\n{context}\n\n'
        f'{instruction}'
    )

    try:
        service = claude or ClaudeService()
        model = Config.CLAUDE_MODEL
        response = service.send_message(
            message=user_message,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            temperature=0,
        )
        answer = (response.content or '').strip()
        if not answer:
            logger.error('Product Anthropic success but empty content')
            return 'I got an empty response from the model. Please try again.'
        logger.info(
            'Product Anthropic success broad=%s answer_chars=%s',
            plan.is_broad,
            len(answer),
        )
        return answer
    except Exception as exc:
        logger.error('Product Anthropic failure: %s', type(exc).__name__)
        return 'I could not generate an answer right now. Please try again shortly.'


# Re-export for callers/tests that previously only imported from answer_service
__all__ = [
    'BROAD_MAX_TOKENS',
    'NARROW_MAX_TOKENS',
    'SYSTEM_PROMPT_BROAD',
    'SYSTEM_PROMPT_NARROW',
    'generate_answer',
    'is_channel_allowed',
    'strip_bot_mention',
]
