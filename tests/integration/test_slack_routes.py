"""
Integration tests for Slack Events webhook (isolated, feature-flagged).
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
def slack_env(monkeypatch):
    monkeypatch.setattr('backend.utils.config.Config.SLACK_BOT_ENABLED', True)
    monkeypatch.setattr('backend.utils.config.Config.SLACK_SIGNING_SECRET', 'test-signing-secret')
    monkeypatch.setattr('backend.utils.config.Config.SLACK_BOT_TOKEN', 'xoxb-test-token')
    # Clear in-memory dedupe between tests
    from backend.api.routes import slack_routes
    with slack_routes._seen_lock:
        slack_routes._seen_event_ids.clear()


class TestSlackRoutes:
    def test_disabled_returns_404(self, client, monkeypatch):
        monkeypatch.setattr('backend.utils.config.Config.SLACK_BOT_ENABLED', False)
        response = client.post('/integrations/slack/events', json={'type': 'url_verification'})
        assert response.status_code == 404

    def test_health_endpoint(self, client, slack_env):
        response = client.get('/integrations/slack/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['enabled'] is True
        assert data['signing_secret_configured'] is True
        assert data['bot_token_configured'] is True
        assert 'SLACK_BOT_TOKEN' not in str(data)
        assert 'test-signing-secret' not in str(data)

    def test_url_verification(self, client, slack_env):
        body = json.dumps({'type': 'url_verification', 'challenge': 'abc123'}).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('test-signing-secret', ts, body)
        response = client.post(
            '/integrations/slack/events',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Slack-Request-Timestamp': ts,
                'X-Slack-Signature': sig,
            },
        )
        assert response.status_code == 200
        assert response.get_json()['challenge'] == 'abc123'

    def test_invalid_signature_rejected(self, client, slack_env):
        body = json.dumps({'type': 'event_callback', 'event': {'type': 'app_mention'}}).encode('utf-8')
        ts = str(int(time.time()))
        response = client.post(
            '/integrations/slack/events',
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Slack-Request-Timestamp': ts,
                'X-Slack-Signature': 'v0=deadbeef',
            },
        )
        assert response.status_code == 401

    def test_app_mention_acks_quickly_and_replies(self, client, slack_env):
        payload = {
            'type': 'event_callback',
            'event_id': 'Ev_TEST_1',
            'event': {
                'type': 'app_mention',
                'user': 'U123',
                'channel': 'C123',
                'ts': '1710000000.000100',
                'text': '<@B0BOT> hello',
            },
        }
        body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('test-signing-secret', ts, body)

        with patch('backend.api.routes.slack_routes.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = b'{"ok":true}'
            mock_post.return_value.json.return_value = {'ok': True}

            response = client.post(
                '/integrations/slack/events',
                data=body,
                headers={
                    'Content-Type': 'application/json',
                    'X-Slack-Request-Timestamp': ts,
                    'X-Slack-Signature': sig,
                },
            )
            assert response.status_code == 200
            assert response.get_json()['ok'] is True

            # Allow daemon thread to run
            time.sleep(0.3)
            assert mock_post.called
            kwargs = mock_post.call_args.kwargs
            assert kwargs['json']['channel'] == 'C123'
            assert kwargs['json']['thread_ts'] == '1710000000.000100'
            assert 'Test reply' in kwargs['json']['text']
            # Token must not appear in logs; Authorization header is fine in mock call
            assert kwargs['headers']['Authorization'].startswith('Bearer ')

    def test_duplicate_event_id_not_reprocessed(self, client, slack_env):
        payload = {
            'type': 'event_callback',
            'event_id': 'Ev_DUP',
            'event': {
                'type': 'app_mention',
                'user': 'U123',
                'channel': 'C123',
                'ts': '1710000000.000200',
                'text': '<@B0BOT> again',
            },
        }
        body = json.dumps(payload).encode('utf-8')
        ts = str(int(time.time()))
        sig = _sign('test-signing-secret', ts, body)
        headers = {
            'Content-Type': 'application/json',
            'X-Slack-Request-Timestamp': ts,
            'X-Slack-Signature': sig,
        }

        with patch('backend.api.routes.slack_routes.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.content = b'{"ok":true}'
            mock_post.return_value.json.return_value = {'ok': True}

            r1 = client.post('/integrations/slack/events', data=body, headers=headers)
            r2 = client.post('/integrations/slack/events', data=body, headers=headers)
            assert r1.status_code == 200
            assert r2.status_code == 200
            time.sleep(0.3)
            assert mock_post.call_count == 1
