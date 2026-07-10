"""
API routes for Halo Survey platform.
"""

import csv
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import Blueprint, Response, jsonify, request, g

from ...api.middleware.auth import require_auth
from ...models.halo_survey import (
    ChatMessage,
    HaloSurvey,
    ResponseStatus,
    SurveyResponse,
    SurveySection,
    SurveyStatus,
    default_braze_url_template,
    normalize_slug,
)
from ...services.halo_survey_analyzer import HaloSurveyAnalyzer
from ...services.halo_survey_designer import HaloSurveyDesigner
from ...services.halo_survey_logic import (
    evaluate_end_state,
    validate_required_answers,
)
from ...services.halo_survey_store import HaloSurveyStore
from ...utils.logging import get_logger

logger = get_logger("halo_survey_routes")

halo_survey_bp = Blueprint("halo_survey", __name__)

_store: Optional[HaloSurveyStore] = None
_rate_limit: Dict[str, float] = {}


def _get_store() -> HaloSurveyStore:
    global _store
    if _store is None:
        _store = HaloSurveyStore()
    return _store


def _get_claude():
    container = getattr(g, "service_container", None)
    return container.get_claude_service() if container else None


def _get_designer() -> HaloSurveyDesigner:
    return HaloSurveyDesigner(claude_service=_get_claude())


def _get_analyzer() -> HaloSurveyAnalyzer:
    return HaloSurveyAnalyzer(claude_service=_get_claude())


def _created_by() -> str:
    return request.headers.get("X-Auth-Token", "researcher")[:64]


def _survey_summary(store: HaloSurveyStore, survey: HaloSurvey) -> Dict[str, Any]:
    counts = store.response_count_by_status(survey.survey_id)
    return {
        **survey.to_dict(),
        "response_count": store.response_count(survey.survey_id),
        "response_counts_by_status": counts,
        "public_url": f"/s/{survey.slug}",
    }


def _check_rate_limit(key: str, limit_sec: float = 1.0) -> bool:
    import time

    now = time.time()
    last = _rate_limit.get(key, 0)
    if now - last < limit_sec:
        return False
    _rate_limit[key] = now
    return True


def _metadata_from_request() -> Dict[str, Any]:
    meta = dict(request.args)
    if request.is_json:
        body = request.get_json(silent=True) or {}
        meta.update(body.get("metadata") or {})
    meta["user_agent"] = request.headers.get("User-Agent", "")[:256]
    return meta


# --- Admin: surveys CRUD ---


@halo_survey_bp.route("/api/surveys", methods=["GET"])
@require_auth
def list_surveys():
    store = _get_store()
    surveys = [_survey_summary(store, s) for s in store.list_surveys()]
    return jsonify({"success": True, "surveys": surveys})


@halo_survey_bp.route("/api/surveys", methods=["POST"])
@require_auth
def create_survey():
    try:
        data = request.get_json() or {}
        title = (data.get("title") or "Untitled Survey").strip()
        store = _get_store()
        sections = None
        if data.get("sections"):
            sections = [SurveySection.from_dict(s) for s in data["sections"]]
        survey = store.create_survey(
            title=title,
            slug=data.get("slug", ""),
            description=data.get("description", ""),
            audience=data.get("audience", ""),
            created_by=_created_by(),
            sections=sections,
        )
        return jsonify({"success": True, "survey": _survey_summary(store, survey)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("create_survey failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@halo_survey_bp.route("/api/surveys/<survey_id>", methods=["GET"])
@require_auth
def get_survey(survey_id: str):
    store = _get_store()
    survey = store.get_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    return jsonify({"success": True, "survey": _survey_summary(store, survey)})


@halo_survey_bp.route("/api/surveys/<survey_id>", methods=["PATCH"])
@require_auth
def update_survey(survey_id: str):
    try:
        data = request.get_json() or {}
        store = _get_store()
        survey = store.get_survey(survey_id)
        if not survey:
            return jsonify({"success": False, "error": "Survey not found"}), 404

        if "title" in data:
            survey.title = data["title"].strip() or survey.title
        if "description" in data:
            survey.description = data.get("description", "")
        if "audience" in data:
            survey.audience = data.get("audience", "")
        if "slug" in data and not survey.slug_locked:
            survey.slug = normalize_slug(data["slug"])
        if "sections" in data:
            survey.sections = [SurveySection.from_dict(s) for s in data["sections"]]
        if "braze_url_template" in data:
            survey.braze_url_template = data["braze_url_template"]
        if "status" in data:
            survey.status = SurveyStatus(data["status"])

        survey = store.update_survey(survey)
        return jsonify({"success": True, "survey": _survey_summary(store, survey)})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.error("update_survey failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@halo_survey_bp.route("/api/surveys/<survey_id>", methods=["DELETE"])
@require_auth
def delete_survey(survey_id: str):
    store = _get_store()
    if not store.delete_survey(survey_id):
        return jsonify({"success": False, "error": "Survey not found"}), 404
    return jsonify({"success": True})


@halo_survey_bp.route("/api/surveys/<survey_id>/publish", methods=["POST"])
@require_auth
def publish_survey(survey_id: str):
    store = _get_store()
    survey = store.publish_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    return jsonify({"success": True, "survey": _survey_summary(store, survey)})


@halo_survey_bp.route("/api/surveys/<survey_id>/archive", methods=["POST"])
@require_auth
def archive_survey(survey_id: str):
    store = _get_store()
    survey = store.archive_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    return jsonify({"success": True, "survey": _survey_summary(store, survey)})


@halo_survey_bp.route("/api/surveys/<survey_id>/designer/chat", methods=["POST"])
@require_auth
def designer_chat(survey_id: str):
    try:
        data = request.get_json() or {}
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"success": False, "error": "message is required"}), 400

        store = _get_store()
        survey = store.get_survey(survey_id)
        if not survey:
            return jsonify({"success": False, "error": "Survey not found"}), 404

        designer = _get_designer()
        history = designer.chat_messages_from_history(survey.design_chat)
        updated, assistant_msg, errors = designer.chat(survey, message, history)

        if errors:
            return jsonify({
                "success": False,
                "error": "; ".join(errors),
                "assistant_message": assistant_msg,
                "survey": survey.to_dict(),
            }), 422

        user_entry = HaloSurveyDesigner.make_chat_entry("user", message)
        assistant_entry = HaloSurveyDesigner.make_chat_entry("assistant", assistant_msg)
        updated.design_chat = list(survey.design_chat) + [user_entry, assistant_entry]
        store.update_survey(updated)

        return jsonify({
            "success": True,
            "assistant_message": assistant_msg,
            "survey": _survey_summary(store, updated),
        })
    except Exception as exc:
        logger.error("designer_chat failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


# --- Admin: responses ---


@halo_survey_bp.route("/api/surveys/<survey_id>/responses", methods=["GET"])
@require_auth
def list_responses(survey_id: str):
    store = _get_store()
    survey = store.get_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    responses = [r.to_dict() for r in store.list_responses(survey_id)]
    return jsonify({"success": True, "responses": responses})


@halo_survey_bp.route("/api/surveys/<survey_id>/responses/export", methods=["GET"])
@require_auth
def export_responses(survey_id: str):
    store = _get_store()
    survey = store.get_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404

    analyzer = _get_analyzer()
    responses = store.list_responses(survey_id)
    headers, rows = analyzer.responses_to_csv_rows(survey, responses)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)

    filename = f"{survey.slug}-responses.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@halo_survey_bp.route("/api/surveys/<survey_id>/analyze", methods=["POST"])
@require_auth
def analyze_responses(survey_id: str):
    try:
        data = request.get_json() or {}
        store = _get_store()
        survey = store.get_survey(survey_id)
        if not survey:
            return jsonify({"success": False, "error": "Survey not found"}), 404

        responses = store.list_responses(survey_id)
        analyzer = _get_analyzer()
        history = data.get("conversation_history") or []
        result = analyzer.analyze(
            survey,
            responses,
            question=data.get("question"),
            conversation_history=history,
        )
        return jsonify({"success": True, **result})
    except Exception as exc:
        logger.error("analyze failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@halo_survey_bp.route("/api/surveys/<survey_id>/stats", methods=["GET"])
@require_auth
def survey_stats(survey_id: str):
    store = _get_store()
    survey = store.get_survey(survey_id)
    if not survey:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    analyzer = _get_analyzer()
    stats = analyzer.aggregate_stats(survey, store.list_responses(survey_id))
    return jsonify({"success": True, "stats": stats})


# --- Public: respondent ---


@halo_survey_bp.route("/api/s/<slug>", methods=["GET"])
def get_public_survey(slug: str):
    store = _get_store()
    survey = store.get_by_slug(slug)
    if not survey or survey.status != SurveyStatus.ACTIVE:
        return jsonify({"success": False, "error": "Survey not found"}), 404
    return jsonify({"success": True, "survey": survey.to_public_dict()})


@halo_survey_bp.route("/api/s/<slug>/responses", methods=["POST"])
def create_or_submit_response(slug: str):
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(f"submit:{client_ip}"):
        return jsonify({"success": False, "error": "Too many requests"}), 429

    try:
        data = request.get_json() or {}
        store = _get_store()
        survey = store.get_by_slug(slug)
        if not survey or survey.status != SurveyStatus.ACTIVE:
            return jsonify({"success": False, "error": "Survey not found"}), 404

        action = data.get("action", "start")
        if action == "start":
            meta = _metadata_from_request()
            meta.update(data.get("metadata") or {})
            response = SurveyResponse.create(survey.survey_id, survey.slug, meta)
            store.create_response(response)
            return jsonify({
                "success": True,
                "response_id": response.response_id,
                "survey": survey.to_public_dict(),
            })

        response_id = data.get("response_id")
        answers = data.get("answers") or {}
        submit = data.get("submit", False)

        if not response_id:
            return jsonify({"success": False, "error": "response_id required"}), 400

        response = store.get_response(response_id)
        if not response or response.survey_id != survey.survey_id:
            return jsonify({"success": False, "error": "Response not found"}), 404

        if response.status != ResponseStatus.IN_PROGRESS:
            return jsonify({
                "success": False,
                "error": "Response already finalized",
                "status": response.status.value,
            }), 400

        response.answers.update(answers)

        end_message, end_status, _ = evaluate_end_state(survey, response.answers)
        if end_message:
            response.status = end_status or ResponseStatus.INELIGIBLE
            response.end_message = end_message
            response.completed_at = datetime.now(timezone.utc).isoformat()
            store.save_response(response)
            return jsonify({
                "success": True,
                "response_id": response.response_id,
                "status": response.status.value,
                "end_message": end_message,
                "finalized": True,
            })

        if submit:
            missing = validate_required_answers(survey, response.answers)
            if missing:
                return jsonify({
                    "success": False,
                    "error": "Required questions missing",
                    "missing": missing,
                }), 400
            response.status = ResponseStatus.COMPLETE
            response.completed_at = datetime.now(timezone.utc).isoformat()
            store.save_response(response)
            return jsonify({
                "success": True,
                "response_id": response.response_id,
                "status": response.status.value,
                "finalized": True,
            })

        store.save_response(response)
        return jsonify({
            "success": True,
            "response_id": response.response_id,
            "status": response.status.value,
            "saved": True,
        })
    except Exception as exc:
        logger.error("response submit failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@halo_survey_bp.route("/api/s/<slug>/responses/<response_id>", methods=["PATCH"])
def patch_response(slug: str, response_id: str):
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(f"patch:{client_ip}"):
        return jsonify({"success": False, "error": "Too many requests"}), 429

    try:
        data = request.get_json() or {}
        store = _get_store()
        survey = store.get_by_slug(slug)
        if not survey or survey.status != SurveyStatus.ACTIVE:
            return jsonify({"success": False, "error": "Survey not found"}), 404

        response = store.get_response(response_id)
        if not response or response.survey_id != survey.survey_id:
            return jsonify({"success": False, "error": "Response not found"}), 404

        if response.status != ResponseStatus.IN_PROGRESS:
            return jsonify({"success": False, "error": "Response already finalized"}), 400

        if data.get("answers"):
            response.answers.update(data["answers"])

        end_message, end_status, _ = evaluate_end_state(survey, response.answers)
        if end_message:
            response.status = end_status or ResponseStatus.INELIGIBLE
            response.end_message = end_message
            response.completed_at = datetime.now(timezone.utc).isoformat()
        elif data.get("submit"):
            missing = validate_required_answers(survey, response.answers)
            if missing:
                return jsonify({"success": False, "error": "Required questions missing", "missing": missing}), 400
            response.status = ResponseStatus.COMPLETE
            response.completed_at = datetime.now(timezone.utc).isoformat()

        store.save_response(response)
        return jsonify({
            "success": True,
            "response_id": response.response_id,
            "status": response.status.value,
            "end_message": response.end_message,
            "finalized": response.status != ResponseStatus.IN_PROGRESS,
        })
    except Exception as exc:
        logger.error("patch response failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500
