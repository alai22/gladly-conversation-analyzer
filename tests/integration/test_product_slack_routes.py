"""
Integration tests for Product Bot Slack Events webhook (isolated).
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest


def _sign(secret: str, timestamp: str, body: bytes) -> str:
    basestring = f'v0:{timestamp}:'.encode('utf-8') + body
    digest = hmac.new(secret.encode('utf-8'), basestring, hashlib.sha256).hexdigest()
    return f'v0={digest}'


@pytest.fixture
def product_slack_env(monkeypatch):
    monkeypatch.setattr('backend.utils.config.Config.PRODUCT_BOT_ENABLED', True)
    monkeypatch.setattr(
        'backend.utils.config.Config.PRODUCT_SLACK_SIGNING_SECRET',
        'product-signing-secret',
    )
    monkeypatch.setattr(
        'backend.utils.config.Config.PRODUCT_SLACK_BOT_TOKEN',
        'xoxb-product-token',
    )
    monkeypatch.setattr(
        'backend.utils.config.Config.PRODUCT_NOTION_TOKEN',
        'secret_product_notion',
    )
    monkeypatch.setattr(
        'backend.utils.config.Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS',
        'page-aaa',
    )
    from backend.api.routes import product_slack_routes
    with product_slack_routes._seen_lock:
        product_slack_routes._seen_event_ids.clear()


class TestProductSlackRoutes:
    def test_disabled_returns_404(self, client, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.PRODUCT_BOT_ENABLED', False)
        response = client.post(
            '/integrations/slack/product/events',
            json={'type': 'url_verification'},
        )
        assert response.status_code == 404

    def test_health_endpoint(self, client, product_slack_env):
        response = client.get('/integrations/slack/product/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['bot'] == 'product'
        assert data['enabled'] is True
        assert data['signing_secret_configured'] is True
        assert data['bot_token_configured'] is True
        assert data['notion_page_filter_configured'] is True
        assert 'xoxb-product-token' not in str(data)
        assert 'product-signing-secret' not in str(data)

    def test_url_verification(self, client, product_slack_env):
        body = json.dumps({'type': 'url_verification', 'challenge': 'prod123'}).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('product-signing-secret', ts, body)
        response = client.post(
            '/integrations/slack/product/events',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Slack-Request-Timestamp': ts,
                'X-Slack-Signature': sig,
            },
        )
        assert response.status_code == 200
        assert response.get_json()['challenge'] == 'prod123'

    def test_ops_signing_secret_rejected(self, client, product_slack_env):
        """Ops bot secret must not authenticate Product Bot requests."""
        body = json.dumps({'type': 'url_verification', 'challenge': 'x'}).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('ops-signing-secret', ts, body)
        response = client.post(
            '/integrations/slack/product/events',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Slack-Request-Timestamp': ts,
                'X-Slack-Signature': sig,
            },
        )
        assert response.status_code == 401

    def test_app_mention_acks_quickly_and_replies(self, client, product_slack_env):
        payload = {
            'type': 'event_callback',
            'event_id': 'Ev_PRODUCT_1',
            'event': {
                'type': 'app_mention',
                'user': 'U123',
                'channel': 'C123',
                'ts': '1710000000.000100',
                'text': '<@B0PRODUCT> roadmap?',
            },
        }
        body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('product-signing-secret', ts, body)

        with patch(
            'backend.api.routes.product_slack_routes.generate_answer',
            return_value='Product grounded answer',
        ) as mock_answer, patch(
            'backend.api.routes.product_slack_routes.requests.post'
        ) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = b'{"ok":true}'
            mock_post.return_value.json.return_value = {'ok': True}

            response = client.post(
                '/integrations/slack/product/events',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-Slack-Request-Timestamp': ts,
                    'X-Slack-Signature': sig,
                },
            )
            assert response.status_code == 200
            assert response.get_json()['ok'] is True

            time.sleep(0.3)
            assert mock_answer.called
            assert mock_answer.call_args.args[0] == 'roadmap?'
            assert mock_post.called
            kwargs = mock_post.call_args.kwargs
            assert kwargs['json']['channel'] == 'C123'
            assert kwargs['json']['thread_ts'] == '1710000000.000100'
            assert kwargs['json']['text'] == 'Product grounded answer'
            assert kwargs['headers']['Authorization'] == 'Bearer xoxb-product-token'

    def test_channel_allowlist_blocks(self, client, product_slack_env, monkeypatch):
        monkeypatch.setattr(
            'backend.utils.config.Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS',
            'C999',
        )
        payload = {
            'type': 'event_callback',
            'event_id': 'Ev_PRODUCT_BLOCKED',
            'event': {
                'type': 'app_mention',
                'user': 'U123',
                'channel': 'C123',
                'ts': '1710000000.000300',
                'text': '<@B0PRODUCT> secret?',
            },
        }
        body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('product-signing-secret', ts, body)

        with patch(
            'backend.api.routes.product_slack_routes.generate_answer'
        ) as mock_answer, patch(
            'backend.api.routes.product_slack_routes.requests.post'
        ) as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = b'{"ok":true}'
            mock_post.return_value.json.return_value = {'ok': True}

            response = client.post(
                '/integrations/slack/product/events',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-Slack-Request-Timestamp': ts,
                    'X-Slack-Signature': sig,
                },
            )
            assert response.status_code == 200
            time.sleep(0.3)
            assert not mock_answer.called
            assert mock_post.called
            assert 'PRODUCT_SLACK_ALLOWED_CHANNEL_IDS' in mock_post.call_args.kwargs['json']['text']
