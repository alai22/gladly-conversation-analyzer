"""
Product Bot Notion retrieval: classify, rank, and load multi-page context.

Isolated from the Operations bot. Uses read-only NotionClient primitives with
Product-specific breadth, title/hub ranking, and deeper page loading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.services.slack_bot.notion_client import NotionClient
from backend.utils.logging import get_logger

logger = get_logger('product_bot.retrieval')

# Retrieval knobs (hardcoded for v1 — no new env required beyond optional priority IDs)
NARROW_SEARCH_LIMIT = 5
BROAD_SEARCH_LIMIT = 12
NARROW_LOAD_PAGES = 3
BROAD_LOAD_PAGES = 5
NARROW_MAX_CHARS = 10000
BROAD_MAX_CHARS = 24000
NARROW_MAX_BLOCKS = 40
BROAD_MAX_BLOCKS = 100
NARROW_MAX_DEPTH = 0
BROAD_MAX_DEPTH = 2
PER_PAGE_CHAR_FLOOR = 800
PRIORITY_PAGE_BOOST = 50.0
THIN_BODY_CHARS = 400

HUB_TITLE_KEYWORDS = frozenset({
    'strategy',
    'roadmap',
    'okr',
    'okrs',
    'charter',
    'vision',
    'overview',
    'index',
    'hub',
    'prd',
    'market',
    'delivery',
    'onboarding',
})

# Conversational prefixes that signal a broad topic/overview question.
_BROAD_PREFIXES = (
    r'tell\s+me\s+about',
    r'tell\s+us\s+about',
    r'what\s+is',
    r'what\s+are',
    r"what's",
    r'whats',
    r'overview\s+of',
    r'give\s+me\s+(?:(?:an|a|the)\s+)?overview\s+(?:of|on|for)',
    r'give\s+me\s+(?:(?:an|a|the)\s+)?summary\s+(?:of|on|for)',
    r'summarize',
    r'summarise',
    r'summary\s+of',
    r'explain',
    r'describe',
    r'can\s+you\s+(?:tell|explain|describe|summarize|summarise)',
)

_BROAD_RE = re.compile(
    r'^\s*(?:' + r'|'.join(_BROAD_PREFIXES) + r')\s+',
    re.IGNORECASE,
)

_TRAILING_PUNCT_RE = re.compile(r'[\s?!.]+$')
_TOKEN_RE = re.compile(r'[a-z0-9]+', re.IGNORECASE)


@dataclass(frozen=True)
class QueryPlan:
    """Classified user question for Product Bot retrieval."""

    original: str
    search_query: str
    is_broad: bool
    topic: str


@dataclass
class RankedHit:
    item: Dict[str, Any]
    title: str
    score: float
    is_hub: bool
    obj: str


@dataclass
class RetrievalResult:
    """Outcome of Product Bot Notion retrieval (no page bodies in logs)."""

    context: str
    plan: QueryPlan
    evidence: str  # 'none' | 'thin' | 'strong'
    candidate_count: int = 0
    loaded_count: int = 0
    body_chars: int = 0
    ranked_preview: List[str] = field(default_factory=list)


def classify_query(question: str) -> QueryPlan:
    """
    Detect broad overview vs narrow factual questions and extract a search topic.
    """
    original = (question or '').strip()
    cleaned = _TRAILING_PUNCT_RE.sub('', original).strip()
    match = _BROAD_RE.match(cleaned)
    is_broad = match is not None
    if is_broad:
        topic = cleaned[match.end():].strip()
        topic = _TRAILING_PUNCT_RE.sub('', topic).strip()
        if not topic:
            topic = cleaned
    else:
        # "halo health overview" / "halo health summary" without leading verb
        lower = cleaned.lower()
        if lower.endswith(' overview') or lower.endswith(' summary'):
            is_broad = True
            topic = re.sub(r'\s+(overview|summary)\s*$', '', cleaned, flags=re.I).strip()
        else:
            topic = cleaned

    search_query = topic or cleaned or original
    plan = QueryPlan(
        original=original,
        search_query=search_query,
        is_broad=is_broad,
        topic=topic or search_query,
    )
    logger.info(
        'Product query classified broad=%s topic_len=%s search_len=%s',
        plan.is_broad,
        len(plan.topic),
        len(plan.search_query),
    )
    return plan


def _tokenize(text: str) -> frozenset:
    return frozenset(t.lower() for t in _TOKEN_RE.findall(text or '') if len(t) > 1)


def _title_is_hub(title: str) -> bool:
    tokens = _tokenize(title)
    title_lower = (title or '').lower()
    if tokens & HUB_TITLE_KEYWORDS:
        return True
    return any(kw in title_lower for kw in HUB_TITLE_KEYWORDS)


def score_title(
    title: str,
    topic: str,
    obj: str,
    *,
    page_id: str = '',
    priority_page_ids: Optional[frozenset] = None,
) -> tuple[float, bool]:
    """
    Rank a Notion hit by title relevance to the topic.

    Higher is better. Does not use last_edited_time.
    Optional priority_page_ids apply a ranking boost only (never required).
    """
    title_norm = (title or '').strip().lower()
    topic_norm = (topic or '').strip().lower()
    is_hub = _title_is_hub(title)
    score = 0.0
    priority = priority_page_ids or frozenset()

    if not title_norm:
        return (-5.0 if obj == 'database' else 0.0, is_hub)

    if topic_norm and title_norm == topic_norm:
        score += 100.0
    elif topic_norm and topic_norm in title_norm:
        score += 60.0
    elif topic_norm and title_norm in topic_norm and len(title_norm) >= 4:
        score += 40.0

    topic_tokens = _tokenize(topic_norm)
    title_tokens = _tokenize(title_norm)
    if topic_tokens and title_tokens:
        overlap = len(topic_tokens & title_tokens)
        score += overlap * 12.0
        if overlap == 0 and len(topic_tokens) >= 2:
            score -= 15.0

    if is_hub:
        score += 25.0

    if obj == 'database':
        score -= 20.0

    if page_id and page_id.lower() in priority:
        score += PRIORITY_PAGE_BOOST

    return score, is_hub


def rank_search_results(
    results: Sequence[Dict[str, Any]],
    topic: str,
    *,
    page_title_fn,
    priority_page_ids: Optional[frozenset] = None,
) -> List[RankedHit]:
    ranked: List[RankedHit] = []
    for item in results:
        obj = item.get('object') or ''
        if obj not in ('page', 'database'):
            continue
        title = page_title_fn(item)
        page_id = item.get('id') or ''
        score, is_hub = score_title(
            title,
            topic,
            obj,
            page_id=page_id,
            priority_page_ids=priority_page_ids,
        )
        ranked.append(
            RankedHit(item=item, title=title, score=score, is_hub=is_hub, obj=obj)
        )
    ranked.sort(key=lambda h: h.score, reverse=True)
    return ranked


def _passes_allowlist(
    item: Dict[str, Any],
    allowed_pages: frozenset,
    allowed_dbs: frozenset,
) -> bool:
    obj = item.get('object')
    item_id = (item.get('id') or '').lower()
    if obj == 'page' and allowed_pages and item_id not in allowed_pages:
        return False
    if obj == 'database' and allowed_dbs and item_id not in allowed_dbs:
        return False
    if allowed_pages and not allowed_dbs and obj == 'database':
        return False
    if allowed_dbs and not allowed_pages and obj == 'page':
        return False
    return True


def _assess_evidence(loaded_count: int, body_chars: int) -> str:
    """Classify retrieval quality after full-page loads (not snippets alone)."""
    if loaded_count <= 0 or body_chars <= 0:
        return 'none'
    if body_chars < THIN_BODY_CHARS:
        return 'thin'
    return 'strong'


def build_product_context(
    notion: NotionClient,
    question: str,
    *,
    allowed_page_ids: Optional[frozenset] = None,
    allowed_database_ids: Optional[frozenset] = None,
    priority_page_ids: Optional[frozenset] = None,
    plan: Optional[QueryPlan] = None,
) -> RetrievalResult:
    """
    Search, rank, and load Product Notion context for a question.

    Loads full page content for top ranked hits (not search snippets alone).
    """
    plan = plan or classify_query(question)
    allowed_pages = allowed_page_ids if allowed_page_ids is not None else frozenset()
    allowed_dbs = allowed_database_ids if allowed_database_ids is not None else frozenset()
    priority = priority_page_ids if priority_page_ids is not None else frozenset()

    search_limit = BROAD_SEARCH_LIMIT if plan.is_broad else NARROW_SEARCH_LIMIT
    load_pages = BROAD_LOAD_PAGES if plan.is_broad else NARROW_LOAD_PAGES
    max_chars = BROAD_MAX_CHARS if plan.is_broad else NARROW_MAX_CHARS
    max_blocks = BROAD_MAX_BLOCKS if plan.is_broad else NARROW_MAX_BLOCKS
    max_depth = BROAD_MAX_DEPTH if plan.is_broad else NARROW_MAX_DEPTH

    results = notion.search(plan.search_query, page_size=search_limit)
    filtered = [
        item for item in results
        if _passes_allowlist(item, allowed_pages, allowed_dbs)
    ]
    ranked = rank_search_results(
        filtered,
        plan.topic,
        page_title_fn=notion._page_title,
        priority_page_ids=priority,
    )

    # Soft floor: drop strongly off-topic hits when we have better ones
    if ranked and plan.topic:
        top_score = ranked[0].score
        if top_score >= 40:
            ranked = [h for h in ranked if h.score >= 0] or ranked[:1]

    to_load = ranked[:load_pages]
    excerpts: List[str] = []
    used = 0
    pages_used = 0
    body_chars = 0

    for idx, hit in enumerate(to_load):
        remaining = max_chars - used
        if remaining <= 0:
            break
        per_page_budget = max(PER_PAGE_CHAR_FLOOR, remaining // max(1, load_pages - idx))
        per_page_budget = min(per_page_budget, remaining)

        if hit.obj == 'page':
            body = notion.fetch_page_text(
                hit.item['id'],
                max_blocks=max_blocks,
                max_chars=per_page_budget,
                max_depth=max_depth,
            )
            body_chars += len(body or '')
            role = (
                'Primary source'
                if idx == 0
                else 'Supporting source'
            )
            if idx == 0 and hit.is_hub:
                role = 'Primary source (hub)'
            chunk = f'### {hit.title}\n({role})\n{body}'.strip()
        else:
            chunk = (
                f'### Database: {hit.title}\n'
                '(Database matched search; open linked pages for details.)'
            )

        if not chunk:
            continue
        if len(chunk) > remaining:
            chunk = chunk[:remaining] + '\n…'
        excerpts.append(chunk)
        used += len(chunk)
        pages_used += 1

    context = '\n\n'.join(excerpts).strip()
    evidence = _assess_evidence(pages_used, body_chars)

    # Truncated titles + short ids only — never page bodies
    rank_preview = [
        f"{(h.item.get('id') or '')[:8]}:{h.title[:40]}:{h.score:.0f}"
        for h in to_load[:5]
    ]
    logger.info(
        'Product Notion retrieval broad=%s candidates=%s loaded=%s body_chars=%s '
        'evidence=%s ranks=%s',
        plan.is_broad,
        len(ranked),
        pages_used,
        body_chars,
        evidence,
        rank_preview,
    )
    return RetrievalResult(
        context=context,
        plan=plan,
        evidence=evidence,
        candidate_count=len(ranked),
        loaded_count=pages_used,
        body_chars=body_chars,
        ranked_preview=rank_preview,
    )
