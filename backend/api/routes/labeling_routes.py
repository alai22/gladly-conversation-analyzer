"""
API routes for Halo AI labeling: staging process + summaries.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from flask import Blueprint, jsonify, request

from backend.api.middleware.auth import require_admin_auth
from backend.services.labeling_data_analyzer import LabelingDataAnalyzer, format_ui_summary
from backend.services.labeling_ingest_service import LabelingIngestService
from backend.utils.config import Config
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
    "message": None,
}
_STALE_RUNNING_SEC = 2 * 60 * 60  # allow restart if marked running > 2h
_PROCESS_STATUS_KEY = "labeling-jobs/process_status.json"


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


def _s3_client():
    return boto3.client("s3", region_name=Config.S3_REGION or "us-east-1")


def _process_snapshot() -> Dict[str, Any]:
    with _PROCESS_LOCK:
        return {
            "running": bool(_PROCESS_STATE["running"]),
            "started_at": _PROCESS_STATE["started_at"],
            "finished_at": _PROCESS_STATE["finished_at"],
            "last_error": _PROCESS_STATE["last_error"],
            "last_report": _PROCESS_STATE["last_report"],
            "message": _PROCESS_STATE["message"],
        }


def _persist_process_state(state: Dict[str, Any]) -> None:
    """Write job state to S3 so status survives tab close / other workers."""
    bucket = Config.LABELING_S3_BUCKET_NAME
    if not bucket:
        return
    try:
        payload = {
            **state,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _s3_client().put_object(
            Bucket=bucket,
            Key=_PROCESS_STATUS_KEY,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist labeling process status: %s", exc)


def _load_persisted_process_state() -> Optional[Dict[str, Any]]:
    bucket = Config.LABELING_S3_BUCKET_NAME
    if not bucket:
        return None
    try:
        body = _s3_client().get_object(Bucket=bucket, Key=_PROCESS_STATUS_KEY)["Body"].read()
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        return data
    except Exception:  # noqa: BLE001
        return None


def _merge_process_state() -> Dict[str, Any]:
    """Prefer in-memory if this worker is running; else S3 (for other workers / reloads)."""
    mem = _process_snapshot()
    if mem.get("running"):
        return mem
    persisted = _load_persisted_process_state()
    if not persisted:
        return mem
    # If S3 says running but started long ago, treat as stale
    if persisted.get("running") and persisted.get("started_at"):
        try:
            started = datetime.strptime(
                persisted["started_at"], "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - started).total_seconds()
            if age > _STALE_RUNNING_SEC:
                persisted = {
                    **persisted,
                    "running": False,
                    "last_error": persisted.get("last_error")
                    or "Process marked stale (exceeded 2h); you can start again.",
                    "message": "Stale job cleared",
                }
        except Exception:  # noqa: BLE001
            pass
    # Keep last_report from whichever is newer
    if not persisted.get("last_report") and mem.get("last_report"):
        persisted["last_report"] = mem["last_report"]
    return {
        "running": bool(persisted.get("running")),
        "started_at": persisted.get("started_at"),
        "finished_at": persisted.get("finished_at"),
        "last_error": persisted.get("last_error"),
        "last_report": persisted.get("last_report"),
        "message": persisted.get("message"),
    }


def _set_process_state(**kwargs: Any) -> Dict[str, Any]:
    with _PROCESS_LOCK:
        _PROCESS_STATE.update(kwargs)
        snap = {
            "running": bool(_PROCESS_STATE["running"]),
            "started_at": _PROCESS_STATE["started_at"],
            "finished_at": _PROCESS_STATE["finished_at"],
            "last_error": _PROCESS_STATE["last_error"],
            "last_report": _PROCESS_STATE["last_report"],
            "message": _PROCESS_STATE["message"],
        }
    _persist_process_state(snap)
    return snap


def _is_process_busy() -> bool:
    state = _merge_process_state()
    return bool(state.get("running"))


@labeling_bp.route("/status", methods=["GET"])
@require_admin_auth
def labeling_status():
    """Staging vs processed output inventory + process job state."""
    try:
        status = LabelingIngestService().staging_status()
        status["process"] = _merge_process_state()
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
      async: bool (default true) — run in background; poll GET /status
    """
    try:
        body = request.get_json(silent=True) or {}
        dry_run = bool(body.get("dry_run", False))
        clear_output = bool(body.get("clear_output", True))
        # Default async so browser tabs are not held open for long S3 copies
        run_async = bool(body.get("async", True))

        if _is_process_busy():
            state = _merge_process_state()
            return jsonify({
                "success": False,
                "error": "A labeling process job is already running",
                "data": state,
            }), 409

        if run_async:
            _set_process_state(
                running=True,
                started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                finished_at=None,
                last_error=None,
                last_report=None,
                message="Processing staging → extracted-txt…",
            )

            def _worker():
                try:
                    report = LabelingIngestService().process_staging(
                        dry_run=dry_run,
                        clear_output=clear_output,
                    )
                    _cache_clear()
                    _set_process_state(
                        running=False,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        last_report=report,
                        last_error=None,
                        message=(
                            f"Done — copied {report.get('copied', 0)} files, "
                            f"{report.get('sessions', 0)} sessions"
                        ),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Async labeling process failed")
                    _set_process_state(
                        running=False,
                        finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        last_error=str(exc),
                        message="Process failed",
                    )

            threading.Thread(target=_worker, daemon=True).start()
            return jsonify({
                "success": True,
                "async": True,
                "message": "Processing started in background. Safe to leave this page.",
                "data": _merge_process_state(),
            })

        _set_process_state(
            running=True,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            finished_at=None,
            last_error=None,
            message="Processing staging → extracted-txt…",
        )
        try:
            report = LabelingIngestService().process_staging(
                dry_run=dry_run,
                clear_output=clear_output,
            )
            _cache_clear()
            state = _set_process_state(
                running=False,
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                last_report=report,
                last_error=None,
                message=f"Done — copied {report.get('copied', 0)} files",
            )
            return jsonify({"success": True, "async": False, "data": report, "process": state})
        except Exception as exc:  # noqa: BLE001
            _set_process_state(
                running=False,
                finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                last_error=str(exc),
                message="Process failed",
            )
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
