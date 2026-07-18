"""
Product Bot Slack Events API webhook.

Fully isolated from the Operations Slack bot: separate credentials, allowlists,
dedupe store, and routes under /integrations/slack/product.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

import requests
from flask import Blueprint, jsonify, request

from backend.services.product_bot.answer_service import (
    generate_answer,
    is_channel_allowed,
    strip_bot_mention,
)
from backend.utils.config import Config
from backend.utils.logging import get_logger

logger = get_logger('product_slack_routes')

product_slack_bp = Blueprint(
    'product_slack',
    __name__,
    url_prefix='/integrations/slack/product',
)

SLACK_API_POST_MESSAGE = 'https://slack.com/api/chat.postMessage'
SIGNATURE_MAX_AGE_SEC = 60 * 5
DEDUPE_MAX_ENTRIES = 512

_seen_event_ids: OrderedDict[str, float] = OrderedDict()
_seen_lock = threading.Lock()


def _bot_enabled() -> bool:
    return bool(Config.PRODUCT_BOT_ENABLED)


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
    secret = Config.PRODUCT_SLACK_SIGNING_SECRET
    if not secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - ts) > SIGNATURE_MAX_AGE_SEC:
        logger.warning('Product Slack signature rejected: timestamp outside allowed window')
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
    token = Config.PRODUCT_SLACK_BOT_TOKEN
    if not token:
        logger.error('Product Slack reply skipped: PRODUCT_SLACK_BOT_TOKEN not configured')
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
                'Product Slack chat.postMessage failed status=%s error=%s',
                resp.status_code,
                data.get('error', 'unknown'),
            )
        else:
            logger.info(
                'Product Slack reply posted channel=%s thread_ts=%s chars=%s',
                channel,
                thread_ts,
                len(text or ''),
            )
    except Exception as exc:
        logger.error('Product Slack chat.postMessage exception: %s', type(exc).__name__)


def _handle_app_mention(event: dict) -> None:
    if _is_bot_event(event):
        logger.info('Ignoring Product app_mention from bot to avoid loops')
        return

    channel = event.get('channel')
    thread_ts = event.get('thread_ts') or event.get('ts')
    raw_text = event.get('text') or ''

    logger.info(
        'Product app_mention received channel=%s text_len=%s',
        channel,
        len(raw_text),
    )

    if not channel or not thread_ts:
        logger.warning('Product app_mention missing channel or ts; skipping reply')
        return

    if not is_channel_allowed(channel):
        logger.info('Product channel blocked channel=%s', channel)
        _post_thread_reply(
            channel,
            thread_ts,
            'This channel is not enabled for Product Bot. Ask an admin to add it to '
            'PRODUCT_SLACK_ALLOWED_CHANNEL_IDS.',
        )
        return

    logger.info('Product channel allowed channel=%s', channel)
    question = strip_bot_mention(raw_text)
    answer = generate_answer(question)
    _post_thread_reply(channel, thread_ts, answer)


def _dispatch_event_async(payload: dict[str, Any]) -> None:
    event = payload.get('event') or {}
    event_type = event.get('type')
    event_id = payload.get('event_id')

    logger.info(
        'Product Slack event_callback received type=%s event_id=%s',
        event_type,
        event_id,
    )

    if event_type == 'app_mention':
        _handle_app_mention(event)
    else:
        logger.info('Ignoring unhandled Product Slack event type=%s', event_type)


@product_slack_bp.route('/health', methods=['GET'])
def product_slack_health():
    """Minimal Product Bot health (no secrets)."""
    return jsonify({
        'status': 'ok',
        'bot': 'product',
        'enabled': _bot_enabled(),
        'signing_secret_configured': bool(Config.PRODUCT_SLACK_SIGNING_SECRET),
        'bot_token_configured': bool(Config.PRODUCT_SLACK_BOT_TOKEN),
        'notion_token_configured': bool(Config.PRODUCT_NOTION_TOKEN),
        'anthropic_configured': bool(Config.ANTHROPIC_API_KEY),
        'channel_allowlist_configured': bool(
            Config.parse_csv_ids(Config.PRODUCT_SLACK_ALLOWED_CHANNEL_IDS)
        ),
        'notion_page_filter_configured': bool(
            Config.parse_csv_ids(Config.PRODUCT_NOTION_ALLOWED_PAGE_IDS)
        ),
        'notion_database_filter_configured': bool(
            Config.parse_csv_ids(Config.PRODUCT_NOTION_ALLOWED_DATABASE_IDS)
        ),
    }), 200


@product_slack_bp.route('/events', methods=['POST'])
def product_slack_events():
    """
    Product Bot Slack Events API endpoint.

    - Verifies request signature with PRODUCT_SLACK_SIGNING_SECRET
    - Handles url_verification challenge
    - Acks event_callback quickly; replies to app_mention asynchronously
    """
    if not _bot_enabled():
        logger.info('Product Slack webhook disabled (PRODUCT_BOT_ENABLED=false)')
        return jsonify({'error': 'not_found'}), 404

    if not Config.PRODUCT_SLACK_SIGNING_SECRET:
        logger.error('Product Slack webhook misconfigured: PRODUCT_SLACK_SIGNING_SECRET missing')
        return jsonify({'error': 'misconfigured'}), 503

    raw_body = request.get_data(cache=True, as_text=False) or b''
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    if not _verify_slack_signature(raw_body, timestamp, signature):
        logger.warning('Product Slack signature verification failed')
        return jsonify({'error': 'invalid_signature'}), 401

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        logger.warning('Product Slack payload parse failed')
        return jsonify({'error': 'invalid_payload'}), 400

    payload_type = payload.get('type')

    if payload_type == 'url_verification':
        challenge = payload.get('challenge')
        logger.info('Product Slack URL verification challenge received')
        return jsonify({'challenge': challenge}), 200

    if payload_type == 'event_callback':
        event_id = payload.get('event_id')
        if _remember_event_id(event_id):
            logger.info(
                'Duplicate Product Slack event ignored event_id=%s type=%s',
                event_id,
                (payload.get('event') or {}).get('type'),
            )
            return jsonify({'ok': True}), 200

        thread = threading.Thread(
            target=_dispatch_event_async,
            args=(payload,),
            daemon=True,
            name='ProductSlackEventDispatch',
        )
        thread.start()
        return jsonify({'ok': True}), 200

    logger.info('Unhandled Product Slack payload type=%s', payload_type)
    return jsonify({'ok': True}), 200
