"""
Unit tests for Product Bot retrieval (classify, rank, context build).
"""

from unittest.mock import MagicMock

from backend.services.product_bot.retrieval import (
    BROAD_LOAD_PAGES,
    BROAD_SEARCH_LIMIT,
    NARROW_LOAD_PAGES,
    NARROW_SEARCH_LIMIT,
    PRIORITY_PAGE_BOOST,
    build_product_context,
    classify_query,
    rank_search_results,
    score_title,
)
from backend.services.slack_bot.notion_client import NotionClient


def _page(page_id: str, title: str) -> dict:
    return {
        'object': 'page',
        'id': page_id,
        'properties': {
            'Name': {
                'type': 'title',
                'title': [{'plain_text': title}],
            }
        },
    }


def _database(db_id: str, title: str) -> dict:
    return {
        'object': 'database',
        'id': db_id,
        'title': [{'plain_text': title}],
    }


def _search_page_size(mock_search) -> int:
    kwargs = mock_search.call_args.kwargs
    if 'page_size' in kwargs:
        return kwargs['page_size']
    return mock_search.call_args.args[1]


class TestClassifyQuery:
    def test_tell_me_about_is_broad(self):
        plan = classify_query('tell me about halo health')
        assert plan.is_broad is True
        assert plan.search_query.lower() == 'halo health'
        assert plan.topic.lower() == 'halo health'

    def test_what_is_is_broad(self):
        plan = classify_query('what is Halo Health?')
        assert plan.is_broad is True
        assert plan.topic.lower() == 'halo health'

    def test_overview_of_is_broad(self):
        plan = classify_query('give me the overview of halo health')
        assert plan.is_broad is True
        assert 'halo health' in plan.topic.lower()

    def test_summarize_is_broad(self):
        plan = classify_query('summarize the collar warranty policy')
        assert plan.is_broad is True
        assert 'collar warranty' in plan.topic.lower()

    def test_trailing_overview_is_broad(self):
        plan = classify_query('halo health overview')
        assert plan.is_broad is True
        assert plan.topic.lower() == 'halo health'

    def test_narrow_factual_stays_narrow(self):
        plan = classify_query('warranty length for Halo collar')
        assert plan.is_broad is False
        assert plan.search_query == 'warranty length for Halo collar'


class TestScoreAndRank:
    def test_exact_title_beats_tangential(self):
        exact, _ = score_title('Halo Health', 'halo health', 'page')
        tangential, _ = score_title('Weekly standup notes', 'halo health', 'page')
        assert exact > tangential

    def test_hub_keyword_boosts(self):
        hub, is_hub = score_title('Halo Health Strategy & Roadmap', 'halo health', 'page')
        plain, plain_hub = score_title('Halo Health random notes', 'halo health', 'page')
        assert is_hub is True
        assert plain_hub is False
        assert hub > plain

    def test_database_soft_penalty(self):
        page_score, _ = score_title('Halo Health', 'halo health', 'page')
        db_score, _ = score_title('Halo Health', 'halo health', 'database')
        assert page_score > db_score

    def test_priority_page_id_boost(self):
        base, _ = score_title('Halo Health notes', 'halo health', 'page', page_id='aaa')
        boosted, _ = score_title(
            'Halo Health notes',
            'halo health',
            'page',
            page_id='aaa',
            priority_page_ids=frozenset({'aaa'}),
        )
        assert boosted == base + PRIORITY_PAGE_BOOST

    def test_rank_orders_by_score_not_input_order(self):
        results = [
            _page('1', 'Unrelated standup'),
            _page('2', 'Halo Health Strategy'),
            _page('3', 'Random wiki'),
            _database('4', 'Halo Health'),
        ]
        ranked = rank_search_results(
            results,
            'halo health',
            page_title_fn=NotionClient._page_title,
        )
        assert ranked[0].title == 'Halo Health Strategy'
        assert ranked[0].is_hub is True

    def test_priority_id_can_outrank_peer(self):
        results = [
            _page('priority-1', 'Halo Health notes'),
            _page('other-1', 'Halo Health draft'),
        ]
        ranked = rank_search_results(
            results,
            'halo health',
            page_title_fn=NotionClient._page_title,
            priority_page_ids=frozenset({'priority-1'}),
        )
        assert ranked[0].item['id'] == 'priority-1'


class TestBuildProductContext:
    def test_broad_uses_wider_search_and_loads_top_pages(self):
        notion = MagicMock()
        notion.search.return_value = [
            _page('aaa', 'Unrelated standup'),
            _page('bbb', 'Halo Health Strategy Roadmap'),
            _page('ccc', 'Halo Health OKRs'),
            _page('ddd', 'Halo Health Pod Charter'),
            _page('eee', 'Market analysis Halo Health'),
            _page('fff', 'Other doc'),
        ]
        notion._page_title = NotionClient._page_title
        notion.fetch_page_text.return_value = (
            'Page body about Halo Health vision and roadmap. ' * 20
        )

        result = build_product_context(
            notion,
            'tell me about halo health',
        )
        assert result.plan.is_broad is True
        assert result.evidence == 'strong'
        assert _search_page_size(notion.search) == BROAD_SEARCH_LIMIT
        # Soft off-topic filter may drop weak titles; still load multiple top pages.
        assert 3 <= notion.fetch_page_text.call_count <= BROAD_LOAD_PAGES
        assert notion.fetch_page_text.call_args.kwargs.get('max_depth') == 2
        assert 'Primary source' in result.context
        assert 'Halo Health Strategy Roadmap' in result.context
        # Highest-ranked hub should be loaded first
        first_id = notion.fetch_page_text.call_args_list[0].args[0]
        assert first_id == 'bbb'

    def test_loads_full_pages_not_snippets_alone(self):
        notion = MagicMock()
        notion.search.return_value = [_page('hub-1', 'Halo Health Strategy')]
        notion._page_title = NotionClient._page_title
        notion.fetch_page_text.return_value = (
            'Full page content from blocks API with enough substance for synthesis. ' * 10
        )

        result = build_product_context(notion, 'tell me about halo health')
        assert notion.fetch_page_text.called
        assert 'Full page content from blocks API' in result.context
        assert result.evidence == 'strong'

    def test_thin_evidence_when_bodies_tiny(self):
        notion = MagicMock()
        notion.search.return_value = [_page('hub-1', 'Halo Health Strategy')]
        notion._page_title = NotionClient._page_title
        notion.fetch_page_text.return_value = 'x'

        result = build_product_context(notion, 'tell me about halo health')
        assert result.evidence == 'thin'
        assert result.loaded_count == 1

    def test_none_evidence_when_no_hits(self):
        notion = MagicMock()
        notion.search.return_value = []
        notion._page_title = NotionClient._page_title

        result = build_product_context(notion, 'tell me about halo health')
        assert result.evidence == 'none'
        assert result.context == ''
        assert notion.fetch_page_text.call_count == 0

    def test_narrow_keeps_smaller_retrieval(self):
        notion = MagicMock()
        notion.search.return_value = [
            _page('aaa', 'Warranty policy'),
            _page('bbb', 'Other'),
        ]
        notion._page_title = NotionClient._page_title
        notion.fetch_page_text.return_value = 'Warranty is 1 year.'

        result = build_product_context(
            notion,
            'warranty length for Halo collar',
        )
        assert result.plan.is_broad is False
        assert _search_page_size(notion.search) == NARROW_SEARCH_LIMIT
        assert notion.fetch_page_text.call_count <= NARROW_LOAD_PAGES
        assert notion.fetch_page_text.call_args.kwargs.get('max_depth', 0) == 0
        assert 'Warranty' in result.context

    def test_allowlist_filters_pages(self):
        notion = MagicMock()
        notion.search.return_value = [
            _page('page-allowed', 'Halo Health Strategy'),
            _page('page-blocked', 'Halo Health Notes'),
        ]
        notion._page_title = NotionClient._page_title
        notion.fetch_page_text.return_value = 'Allowed body with enough characters for strong evidence xx'

        result = build_product_context(
            notion,
            'tell me about halo health',
            allowed_page_ids=frozenset({'page-allowed'}),
        )
        loaded_ids = [
            call.args[0] for call in notion.fetch_page_text.call_args_list
        ]
        assert loaded_ids == ['page-allowed']
        assert 'Halo Health Strategy' in result.context
