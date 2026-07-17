"""
Minimal Slack Events API webhook.

Isolated from core business logic. Feature-flagged via SLACK_BOT_ENABLED.
Handles signature verification, URL challenge, and hardcoded app_mention replies.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict
from typing import Any

import requests
from flask import Blueprint, jsonify, request

from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('slack_routes')

slack_bp = Blueprint('slack', __name__, url_prefix='/integrations/slack')

SLACK_API_POST_MESSAGE = 'https://slack.com/api/chat.postMessage'
TEST_REPLY_TEXT = 'Test reply from the Slack bot webhook.'
SIGNATURE_MAX_AGE_SEC = 60 * 5
DEDUPE_MAX_ENTRIES = 512

# Process-local dedupe for Slack retries (event_id). Non-persistent; enough for short retries.
_seen_event_ids: OrderedDict[str, float] = OrderedDict()
_seen_lock = threading.Lock()


def _slack_enabled() -> bool:
    return bool(Config.SLACK_BOT_ENABLED)


def _remember_event_id(event_id: Optional[str]) -> bool:
    """Return True if this event_id was already seen (duplicate)."""
    if not event_id:
        return False
    with _seen_lock:
        if event_id in _seen_event_ids:
            return True
        _seen_event_ids[event_id] = time.time()
        while len(_seen_event_ids) > DEDUPE_MAX_ENTRIES:
            _seen_event_ids.popitem(last=False)
        return False


def _verify_slack_signature(raw_body: bytes, timestamp: str, signature: str) -> bool:
    secret = Config.SLACK_SIGNING_SECRET
    if not secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > SIGNATURE_MAX_AGE_SEC:
        logger.warning('Slack signature rejected: timestamp outside allowed window')
        return False

    basestring = f'v0:{timestamp}:'.encode('utf-8') + raw_body
    digest = hmac.new(secret.encode('utf-8'), basestring, hashlib.sha256).hexdigest()
    expected = f'v0={digest}'
    return hmac.compare_digest(expected, signature)


def _is_bot_event(event: dict) -> bool:
    if event.get('bot_id'):
        return True
    if event.get('subtype') == 'bot_message':
        return True
    if event.get('bot_profile'):
        return True
    return False


def _post_thread_reply(channel: str, thread_ts: str, text: str) -> None:
    token = Config.SLACK_BOT_TOKEN
    if not token:
        logger.error('Slack reply skipped: SLACK_BOT_TOKEN not configured')
        return
    try:
        resp = requests.post(
            SLACK_API_POST_MESSAGE,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json; charset=utf-8',
            },
            json={
                'channel': channel,
                'thread_ts': thread_ts,
                'text': text,
            },
            timeout=10,
        )
        data = resp.json() if resp.content else {}
        if not data.get('ok'):
            logger.error(
                'Slack chat.postMessage failed status=%s error=%s',
                resp.status_code,
                data.get('error', 'unknown'),
            )
        else:
            logger.info(
                'Slack test reply sent channel=%s thread_ts=%s',
                channel,
                thread_ts,
            )
    except Exception as exc:
        logger.error('Slack chat.postMessage exception: %s', type(exc).__name__)


def _handle_app_mention(event: dict) -> None:
    if _is_bot_event(event):
        logger.info('Ignoring app_mention from bot to avoid loops')
        return
    channel = event.get('channel')
    thread_ts = event.get('thread_ts') or event.get('ts')
    if not channel or not thread_ts:
        logger.warning('app_mention missing channel or ts; skipping reply')
        return
    _post_thread_reply(channel, thread_ts, TEST_REPLY_TEXT)


def _dispatch_event_async(payload: dict[str, Any]) -> None:
    event = payload.get('event') or {}
    event_type = event.get('type')
    event_id = payload.get('event_id')

    logger.info('Slack event_callback received type=%s event_id=%s', event_type, event_id)

    if event_type == 'app_mention':
        _handle_app_mention(event)
    else:
        logger.info('Ignoring unhandled Slack event type=%s', event_type)


@slack_bp.route('/health', methods=['GET'])
def slack_health():
    """Minimal Slack integration health (no secrets)."""
    return jsonify({
        'status': 'ok',
        'enabled': _slack_enabled(),
        'signing_secret_configured': bool(Config.SLACK_SIGNING_SECRET),
        'bot_token_configured': bool(Config.SLACK_BOT_TOKEN),
    }), 200


@slack_bp.route('/events', methods=['POST'])
def slack_events():
    """
    Slack Events API endpoint.

    - Verifies request signature
    - Handles url_verification challenge
    - Acks event_callback quickly; replies to app_mention asynchronously
    """
    if not _slack_enabled():
        logger.info('Slack webhook disabled (SLACK_BOT_ENABLED=false)')
        return jsonify({'error': 'not_found'}), 404

    if not Config.SLACK_SIGNING_SECRET:
        logger.error('Slack webhook misconfigured: SLACK_SIGNING_SECRET missing')
        return jsonify({'error': 'misconfigured'}), 503

    raw_body = request.get_data(cache=True, as_text=False) or b''
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    if not _verify_slack_signature(raw_body, timestamp, signature):
        logger.warning('Slack signature verification failed')
        return jsonify({'error': 'invalid_signature'}), 401

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning('Slack payload parse failed')
        return jsonify({'error': 'invalid_payload'}), 400

    payload_type = payload.get('type')

    if payload_type == 'url_verification':
        challenge = payload.get('challenge')
        logger.info('Slack URL verification challenge received')
        return jsonify({'challenge': challenge}), 200

    if payload_type == 'event_callback':
        event_id = payload.get('event_id')
        if _remember_event_id(event_id):
            logger.info(
                'Duplicate Slack event ignored event_id=%s type=%s',
                event_id,
                (payload.get('event') or {}).get('type'),
            )
            return jsonify({'ok': True}), 200

        # Acknowledge immediately; do work off the request thread.
        thread = threading.Thread(
            target=_dispatch_event_async,
            args=(payload,),
            daemon=True,
            name='SlackEventDispatch',
        )
        thread.start()
        return jsonify({'ok': True}), 200

    logger.info('Unhandled Slack payload type=%s', payload_type)
    return jsonify({'ok': True}), 200
