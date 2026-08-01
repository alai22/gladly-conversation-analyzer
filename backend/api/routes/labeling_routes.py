"""
API routes for Halo AI labeling: staging process + summaries.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from backend.api.middleware.auth import require_admin_auth
from backend.services.labeling_data_analyzer import LabelingDataAnalyzer, format_ui_summary
from backend.services.labeling_ingest_service import LabelingIngestService
from backend.utils.logging import get_logger

logger = get_logger("labeling_routes")

labeling_bp = Blueprint("labeling", __name__, url_prefix="/api/labeling")

_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {"key": None, "expires_at": 0.0, "payload": None}
_DEFAULT_CACHE_TTL_SEC = 120

_PROCESS_LOCK = threading.Lock()
_PROCESS_STATE: Dict[str, Any] = {
    "running": False,
    "started_at": None,
    "finished_at": None,
    "last_report": None,
    "last_error": None,
}


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    with _CACHE_LOCK:
        if _CACHE["key"] != key:
            return None
        if time.time() >= float(_CACHE["expires_at"] or 0):
            return None
        return _CACHE["payload"]


def _cache_set(key: str, payload: Dict[str, Any], ttl_sec: int) -> None:
    with _CACHE_LOCK:
        _CACHE["key"] = key
        _CACHE["payload"] = payload
        _CACHE["expires_at"] = time.time() + max(0, ttl_sec)


def _cache_clear() -> None:
    with _CACHE_LOCK:
        _CACHE["key"] = None
        _CACHE["payload"] = None
        _CACHE["expires_at"] = 0.0


@labeling_bp.route("/status", methods=["GET"])
@require_admin_auth
def labeling_status():
    """Staging vs processed output inventory + last process job state."""
    try:
        status = LabelingIngestService().staging_status()
        with _PROCESS_LOCK:
            status["process"] = {
                "running": _PROCESS_STATE["running"],
                "started_at": _PROCESS_STATE["started_at"],
                "finished_at": _PROCESS_STATE["finished_at"],
                "last_error": _PROCESS_STATE["last_error"],
                "last_report": _PROCESS_STATE["last_report"],
            }
        return jsonify({"success": True, "data": status})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to get labeling status")
        return jsonify({"success": False, "error": str(exc)}), 500


@labeling_bp.route("/process", methods=["POST"])
@require_admin_auth
def labeling_process():
    """
    Process staging/ → extracted-txt/<email>/<collar-sn>/.

    JSON body (optional):
      dry_run: bool (default false)
      clear_output: bool (default true) — wipe extracted-txt before copy
      async: bool (default false) — run in background thread
    """
    try:
        body = request.get_json(silent=True) or {}
        dry_run = bool(body.get("dry_run", False))
        clear_output = bool(body.get("clear_output", True))
        run_async = bool(body.get("async", False))

        with _PROCESS_LOCK:
            if _PROCESS_STATE["running"]:
                return jsonify({
                    "success": False,
                    "error": "A labeling process job is already running",
                    "data": {
                        "running": True,
                        "started_at": _PROCESS_STATE["started_at"],
                    },
                }), 409

        if run_async:
            with _PROCESS_LOCK:
                _PROCESS_STATE["running"] = True
                _PROCESS_STATE["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                _PROCESS_STATE["finished_at"] = None
                _PROCESS_STATE["last_error"] = None
                _PROCESS_STATE["last_report"] = None

            def _worker():
                try:
                    report = LabelingIngestService().process_staging(
                        dry_run=dry_run,
                        clear_output=clear_output,
                    )
                    _cache_clear()
                    with _PROCESS_LOCK:
                        _PROCESS_STATE["last_report"] = report
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Async labeling process failed")
                    with _PROCESS_LOCK:
                        _PROCESS_STATE["last_error"] = str(exc)
                finally:
                    with _PROCESS_LOCK:
                        _PROCESS_STATE["running"] = False
                        _PROCESS_STATE["finished_at"] = time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                        )

            threading.Thread(target=_worker, daemon=True).start()
            return jsonify({
                "success": True,
                "async": True,
                "message": "Processing started",
            })

        with _PROCESS_LOCK:
            _PROCESS_STATE["running"] = True
            _PROCESS_STATE["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _PROCESS_STATE["finished_at"] = None
            _PROCESS_STATE["last_error"] = None
        try:
            report = LabelingIngestService().process_staging(
                dry_run=dry_run,
                clear_output=clear_output,
            )
            _cache_clear()
            with _PROCESS_LOCK:
                _PROCESS_STATE["last_report"] = report
                _PROCESS_STATE["running"] = False
                _PROCESS_STATE["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            return jsonify({"success": True, "async": False, "data": report})
        except Exception as exc:  # noqa: BLE001
            with _PROCESS_LOCK:
                _PROCESS_STATE["last_error"] = str(exc)
                _PROCESS_STATE["running"] = False
                _PROCESS_STATE["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            raise
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process labeling staging")
        return jsonify({"success": False, "error": str(exc)}), 500


@labeling_bp.route("/summary", methods=["GET"])
@require_admin_auth
def labeling_summary():
    """
    Summarize processed labeling exports under extracted-txt/.

    Query params:
      refresh=1  — bypass cache
      ttl=120    — cache TTL seconds (0 disables caching for this response)
    """
    try:
        refresh = request.args.get("refresh", "").lower() in ("1", "true", "yes")
        try:
            ttl = int(request.args.get("ttl", _DEFAULT_CACHE_TTL_SEC))
        except ValueError:
            ttl = _DEFAULT_CACHE_TTL_SEC

        cache_key = "summary:v1"
        if not refresh and ttl > 0:
            cached = _cache_get(cache_key)
            if cached is not None:
                return jsonify({"success": True, "cached": True, "data": cached})

        analyzer = LabelingDataAnalyzer()
        raw = analyzer.analyze(include_content=True)
        data = format_ui_summary(raw)

        if ttl > 0:
            _cache_set(cache_key, data, ttl)

        return jsonify({"success": True, "cached": False, "data": data})
    except ValueError as exc:
        logger.warning("Labeling summary misconfigured: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to build labeling summary")
        return jsonify({"success": False, "error": str(exc)}), 500
