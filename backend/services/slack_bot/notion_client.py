"""
Read-only Notion API client for the Slack bot.

Uses Notion Search over whatever the integration token can access.
Optional page/database ID filters may further narrow results; they are not required.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('slack_bot.notion')

NOTION_VERSION = '2022-06-28'
NOTION_BASE = 'https://api.notion.com/v1'
DEFAULT_SEARCH_LIMIT = 5
DEFAULT_MAX_BLOCKS = 40
DEFAULT_MAX_CHARS = 10000


class NotionReadError(Exception):
    """Raised when a Notion read fails."""


class NotionClient:
    """Minimal read-only Notion client."""

    def __init__(self, token: Optional[str] = None, timeout: int = 15):
        self.token = token or Config.NOTION_TOKEN
        if not self.token:
            raise NotionReadError('NOTION_TOKEN is not configured')
        self.timeout = timeout
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Notion-Version': NOTION_VERSION,
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f'{NOTION_BASE}{path}'
        try:
            resp = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=self.timeout,
                **kwargs,
            )
        except requests.RequestException as exc:
            logger.error('Notion request failed path=%s error=%s', path, type(exc).__name__)
            raise NotionReadError(f'Notion request failed: {type(exc).__name__}') from exc

        if resp.status_code >= 400:
            # Never log response body (may contain workspace content); log status only.
            logger.error('Notion API error path=%s status=%s', path, resp.status_code)
            raise NotionReadError(f'Notion API error status={resp.status_code}')

        try:
            return resp.json() if resp.content else {}
        except ValueError as exc:
            raise NotionReadError('Notion returned invalid JSON') from exc

    def search(self, query: str, page_size: int = DEFAULT_SEARCH_LIMIT) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            'query': query or '',
            'page_size': max(1, min(page_size, 20)),
            'sort': {'direction': 'descending', 'timestamp': 'last_edited_time'},
        }
        data = self._request('POST', '/search', json=payload)
        results = data.get('results') or []
        logger.info('Notion search ok query_len=%s results=%s', len(query or ''), len(results))
        return results

    def get_block_children(self, block_id: str, page_size: int = 50) -> List[Dict[str, Any]]:
        data = self._request(
            'GET',
            f'/blocks/{block_id}/children',
            params={'page_size': page_size},
        )
        return data.get('results') or []

    @staticmethod
    def _rich_text_to_plain(rich_text: Optional[List[Dict[str, Any]]]) -> str:
        if not rich_text:
            return ''
        parts = []
        for item in rich_text:
            plain = item.get('plain_text')
            if plain:
                parts.append(plain)
        return ''.join(parts)

    def _block_to_text(self, block: Dict[str, Any]) -> str:
        btype = block.get('type')
        if not btype:
            return ''
        payload = block.get(btype) or {}
        if isinstance(payload, dict) and 'rich_text' in payload:
            return self._rich_text_to_plain(payload.get('rich_text'))
        if btype == 'child_page':
            return payload.get('title') or ''
        if btype == 'child_database':
            return payload.get('title') or ''
        return ''

    @staticmethod
    def _page_title(page: Dict[str, Any]) -> str:
        props = page.get('properties') or {}
        for prop in props.values():
            if prop.get('type') == 'title':
                title_bits = prop.get('title') or []
                texts = [t.get('plain_text', '') for t in title_bits if t.get('plain_text')]
                if texts:
                    return ''.join(texts)
        # Search results sometimes expose title differently
        if page.get('object') == 'database':
            title_bits = page.get('title') or []
            texts = [t.get('plain_text', '') for t in title_bits if t.get('plain_text')]
            if texts:
                return ''.join(texts)
        return page.get('id', 'Untitled')[:12]

    def fetch_page_text(
        self,
        page_id: str,
        max_blocks: int = DEFAULT_MAX_BLOCKS,
        max_chars: int = DEFAULT_MAX_CHARS,
    ) -> str:
        blocks = self.get_block_children(page_id, page_size=min(100, max_blocks))
        lines: List[str] = []
        total = 0
        for block in blocks[:max_blocks]:
            text = self._block_to_text(block).strip()
            if not text:
                continue
            lines.append(text)
            total += len(text)
            if total >= max_chars:
                break
        content = '\n'.join(lines)
        if len(content) > max_chars:
            content = content[:max_chars] + '\n…'
        return content

    def build_context_for_query(
        self,
        query: str,
        *,
        search_limit: int = DEFAULT_SEARCH_LIMIT,
        max_chars: int = DEFAULT_MAX_CHARS,
        allowed_page_ids: Optional[frozenset] = None,
        allowed_database_ids: Optional[frozenset] = None,
    ) -> str:
        """
        Search Notion and concatenate plain text from top hits.

        Optional allowlists filter results; empty/None means no filter
        (trust Notion integration scope).
        """
        allowed_pages = allowed_page_ids if allowed_page_ids is not None else frozenset()
        allowed_dbs = allowed_database_ids if allowed_database_ids is not None else frozenset()

        results = self.search(query, page_size=search_limit)
        excerpts: List[str] = []
        used = 0
        pages_used = 0

        for item in results:
            obj = item.get('object')
            item_id = (item.get('id') or '').lower()
            if obj == 'page' and allowed_pages and item_id not in allowed_pages:
                continue
            if obj == 'database' and allowed_dbs and item_id not in allowed_dbs:
                continue
            # If only one allowlist type is set, skip the other object type.
            if allowed_pages and not allowed_dbs and obj == 'database':
                continue
            if allowed_dbs and not allowed_pages and obj == 'page':
                continue

            title = self._page_title(item)
            if obj == 'page':
                body = self.fetch_page_text(item['id'], max_chars=max(500, max_chars - used))
                chunk = f'### {title}\n{body}'.strip()
            elif obj == 'database':
                # Databases: include title only for v1 (no write; avoid heavy query unless needed)
                chunk = f'### Database: {title}\n(Database matched search; open linked pages for details.)'
            else:
                continue

            if not chunk:
                continue
            remaining = max_chars - used
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                chunk = chunk[:remaining] + '\n…'
            excerpts.append(chunk)
            used += len(chunk)
            pages_used += 1

        logger.info(
            'Notion context built pages=%s chars=%s filtered_pages=%s filtered_dbs=%s',
            pages_used,
            used,
            bool(allowed_pages),
            bool(allowed_dbs),
        )
        return '\n\n'.join(excerpts).strip()
