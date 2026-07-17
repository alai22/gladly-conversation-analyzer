"""
Unit tests for Slack bot answer orchestration.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.services.slack_bot.answer_service import (
    generate_answer,
    is_channel_allowed,
    strip_bot_mention,
)
from backend.services.slack_bot.notion_client import NotionReadError


class TestStripBotMention:
    def test_strips_mention_and_whitespace(self):
        assert strip_bot_mention('<@B0BOT>  what is  warranty?') == 'what is warranty?'

    def test_empty(self):
        assert strip_bot_mention('') == ''
        assert strip_bot_mention('<@B0BOT>') == ''


class TestChannelAllowlist:
    def test_empty_allowlist_allows_all(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.SLACK_ALLOWED_CHANNEL_IDS', '')
        assert is_channel_allowed('C123') is True

    def test_allowlist_matches_case_insensitive(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.SLACK_ALLOWED_CHANNEL_IDS', 'C123, C456')
        assert is_channel_allowed('c123') is True
        assert is_channel_allowed('C999') is False

    def test_allowlist_rejects_missing_channel(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.SLACK_ALLOWED_CHANNEL_IDS', 'C123')
        assert is_channel_allowed(None) is False


class TestGenerateAnswer:
    def test_empty_question(self):
        assert 'question' in generate_answer('').lower()

    def test_empty_notion_context(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.NOTION_ALLOWED_DATABASE_IDS', '')
        with patch('backend.services.slack_bot.answer_service.NotionClient') as MockNotion:
            MockNotion.return_value.build_context_for_query.return_value = ''
            text = generate_answer('warranty policy?')
            assert 'could not find' in text.lower()

    def test_notion_error_returns_friendly_message(self):
        with patch('backend.services.slack_bot.answer_service.NotionClient') as MockNotion:
            MockNotion.side_effect = NotionReadError('NOTION_TOKEN is not configured')
            text = generate_answer('hello')
            assert 'could not read Notion' in text

    def test_success_path_uses_claude(self, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.NOTION_ALLOWED_PAGE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.NOTION_ALLOWED_DATABASE_IDS', '')
        monkeypatch.setattr('backend.utils.config.Config.SLACK_BOT_MODEL', None)
        monkeypatch.setattr('backend.utils.config.Config.CLAUDE_MODEL', 'claude-haiku-4-5')

        mock_claude = MagicMock()
        mock_claude.send_message.return_value = SimpleNamespace(content='Answer from docs')

        with patch('backend.services.slack_bot.answer_service.NotionClient') as MockNotion:
            MockNotion.return_value.build_context_for_query.return_value = '### Page\nWarranty is 1 year.'
            text = generate_answer('warranty?', claude=mock_claude)

        assert text == 'Answer from docs'
        kwargs = mock_claude.send_message.call_args.kwargs
        assert 'Warranty is 1 year' in kwargs['message']
        assert kwargs['temperature'] == 0
        assert kwargs['model'] == 'claude-haiku-4-5'
