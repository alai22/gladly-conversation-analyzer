"""
Unit tests for Product Bot answer orchestration.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.product_bot.answer_service import (
    BROAD_MAX_TOKENS,
    NARROW_MAX_TOKENS,
    SYSTEM_PROMPT_BROAD,
    SYSTEM_PROMPT_NARROW,
    generate_answer,
    is_channel_allowed,
)
from backend.services.product_bot.retrieval import QueryPlan, RetrievalResult


def _result(context, *, is_broad=False, evidence='strong', question='q'):
    plan = QueryPlan(
        original=question,
        search_query=question,
        is_broad=is_broad,
        topic=question,
    )
    return RetrievalResult(
        context=context,
        plan=plan,
        evidence=evidence,
        candidate_count=1 if context else 0,
        loaded_count=1 if context else 0,
        body_chars=len(context),
        ranked_preview=['abcd:Halo Health Strategy:90'] if context else [],
    )


class TestProductChannelAllowlist:
    def test_empty_allowlist_allows_all(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS', '')
        assert is_channel_allowed('C123') is True

    def test_allowlist_matches(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS',
            'C123',
        )
        assert is_channel_allowed('c123') is True
        assert is_channel_allowed('C999') is False


class TestProductGenerateAnswer:
    def test_empty_question(self):
        assert 'question' in generate_answer('').lower()

    def test_empty_notion_allowlists_searches_integration_scope(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'secret_product',
        )
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.CLAUDE_MODEL', 'claude-haiku-4-5')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='Product answer')

        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result('### Page\nRoadmap', question='roadmap?'),
            ) as mock_build:
                text = generate_answer('roadmap?', claude=mock_claude)

        assert text == 'Product answer'
        MockNotion.assert_called_once_with(token='secret_product')
        kwargs = mock_build.call_args.kwargs
        assert kwargs['allowed_page_ids'] == frozenset()
        assert kwargs['allowed_database_ids'] == frozenset()
        assert kwargs['priority_page_ids'] == frozenset()
        assert mock_claude.send_message.call_args.kwargs['max_tokens'] == NARROW_MAX_TOKENS
        assert mock_claude.send_message.call_args.kwargs['system_prompt'] == SYSTEM_PROMPT_NARROW

    def test_broad_question_uses_overview_prompt(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'secret_product',
        )
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.CLAUDE_MODEL', 'claude-haiku-4-5')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='Overview answer')

        with patch('backend.services.product_bot.answer_service.NotionClient'):
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result(
                    '### Halo Health Strategy\n(Primary source)\nBody',
                    is_broad=True,
                    question='tell me about halo health',
                ),
            ):
                text = generate_answer('tell me about halo health', claude=mock_claude)

        assert text == 'Overview answer'
        kwargs = mock_claude.send_message.call_args.kwargs
        assert kwargs['max_tokens'] == BROAD_MAX_TOKENS
        assert kwargs['system_prompt'] == SYSTEM_PROMPT_BROAD

    def test_none_evidence_fallback(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'secret_product',
        )
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS', '')

        mock_claude = MagicMock()
        with patch('backend.services.product_bot.answer_service.NotionClient'):
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result('', evidence='none'),
            ):
                text = generate_answer('tell me about zzz', claude=mock_claude)

        assert 'no matching docs' in text.lower()
        assert not mock_claude.send_message.called

    def test_thin_evidence_fallback(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'secret_product',
        )
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS', '')

        mock_claude = MagicMock()
        with patch('backend.services.product_bot.answer_service.NotionClient'):
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result('### X\ny', evidence='thin'),
            ):
                text = generate_answer('tell me about halo health', claude=mock_claude)

        assert 'too thin' in text.lower()
        assert not mock_claude.send_message.called

    def test_uses_product_notion_token_and_allowlists(self, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'secret_product',
        )
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS',
            'page-1',
        )
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS',
            '',
        )
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS',
            'hub-1',
        )
        monkeypatch.setattr('backend.utils.config.Config.CLAUDE_MODEL', 'claude-haiku-4-5')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='Product answer')

        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result('### Page\nRoadmap Q3', question='roadmap?'),
            ) as mock_build:
                text = generate_answer('roadmap?', claude=mock_claude)

        assert text == 'Product answer'
        MockNotion.assert_called_once_with(token='secret_product')
        kwargs = mock_build.call_args.kwargs
        assert kwargs['allowed_page_ids'] == frozenset({'page-1'})
        assert kwargs['allowed_database_ids'] == frozenset()
        assert kwargs['priority_page_ids'] == frozenset({'hub-1'})

    def test_does_not_read_ops_notion_token(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.NOTION_TOKEN', 'ops_token')
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'product_token',
        )
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_PRIORITY_PAGE_IDS', '')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='ok')

        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            with patch(
                'backend.services.product_bot.answer_service.build_product_context',
                return_value=_result('ctx'),
            ):
                generate_answer('q', claude=mock_claude)

        MockNotion.assert_called_once_with(token='product_token')
