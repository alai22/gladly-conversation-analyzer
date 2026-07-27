"""
Unit tests for NotionClient.fetch_page_text depth behavior (defaults preserved).
"""

from unittest.mock import MagicMock

from backend.services.slack_bot.notion_client import NotionClient


def _text_block(block_id: str, text: str, has_children: bool = False) -> dict:
    return {
        'id': block_id,
        'type': 'paragraph',
        'has_children': has_children,
        'paragraph': {'rich_text': [{'plain_text': text}]},
    }


def _toggle_block(block_id: str, text: str) -> dict:
    return {
        'id': block_id,
        'type': 'toggle',
        'has_children': True,
        'toggle': {'rich_text': [{'plain_text': text}]},
    }


class TestFetchPageTextDepth:
    def test_default_depth_does_not_recurse(self):
        client = NotionClient(token='secret')
        client.get_block_children = MagicMock(
            side_effect=[
                [_toggle_block('t1', 'Parent'), _text_block('p1', 'Sibling')],
                [_text_block('c1', 'Nested child')],
            ]
        )
        text = client.fetch_page_text('page-1')
        assert 'Parent' in text
        assert 'Sibling' in text
        assert 'Nested child' not in text
        assert client.get_block_children.call_count == 1

    def test_max_depth_recurses_into_children(self):
        client = NotionClient(token='secret')
        client.get_block_children = MagicMock(
            side_effect=[
                [_toggle_block('t1', 'Parent section')],
                [_text_block('c1', 'Nested detail')],
            ]
        )
        text = client.fetch_page_text('page-1', max_depth=1)
        assert 'Parent section' in text
        assert 'Nested detail' in text
        assert client.get_block_children.call_count == 2
