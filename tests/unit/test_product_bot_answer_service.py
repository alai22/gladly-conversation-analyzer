"""
Unit tests for Product Bot answer orchestration.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.services.product_bot.answer_service import (
    generate_answer,
    is_channel_allowed,
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

    def test_fail_closed_without_notion_allowlists(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS', '')
        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            text = generate_answer('roadmap?')
            assert 'not fully configured' in text.lower()
            assert not MockNotion.called

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
        monkeypatch.setattr('backend.utils.config.Config.CLAUDE_MODEL', 'claude-haiku-4-5')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='Product answer')

        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            MockNotion.return_value.build_context_for_query.return_value = '### Page\nRoadmap Q3'
            text = generate_answer('roadmap?', claude=mock_claude)

        assert text == 'Product answer'
        MockNotion.assert_called_once_with(token='secret_product')
        kwargs = MockNotion.return_value.build_context_for_query.call_args.kwargs
        assert kwargs['allowed_page_ids'] == frozenset({'page-1'})
        assert kwargs['allowed_database_ids'] == frozenset()

    def test_does_not_read_ops_notion_token(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.NOTION_TOKEN', 'ops_token')
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
            'product_token',
        )
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS',
            'page-1',
        )
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS',
            '',
        )

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='ok')

        with patch('backend.services.product_bot.answer_service.NotionClient') as MockNotion:
            MockNotion.return_value.build_context_for_query.return_value = 'ctx'
            generate_answer('q', claude=mock_claude)

        MockNotion.assert_called_once_with(token='product_token')
