"""
API routes for AI 1:1 text interviews.
"""

from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request, g, Response

from ...api.middleware.auth import require_auth
from ...models.interview import InterviewConfig, ProjectStatus, SessionStatus
from ...services.interview_agent import InterviewAgent
from ...services.interview_insight_generator import InsightGenerator
from ...services.interview_store import TranscriptStore
from ...utils.logging import get_logger

logger = get_logger("interview_routes")

interview_bp = Blueprint("interview", __name__, url_prefix="/api/interviews")

_store: Optional[TranscriptStore] = None


def _get_store() -> TranscriptStore:
    global _store
    if _store is None:
        _store = TranscriptStore()
    return _store


def _get_agent() -> InterviewAgent:
    container = getattr(g, "service_container", None)
    claude = container.get_claude_service() if container else None
    return InterviewAgent(claude_service=claude)


def _get_insight_generator() -> InsightGenerator:
    container = getattr(g, "service_container", None)
    claude = container.get_claude_service() if container else None
    return InsightGenerator(claude_service=claude)


def _join_url(token: str) -> str:
    return f"/interview/join?t={token}"


def _created_by() -> str:
    return request.headers.get("X-Auth-Token", "researcher")[:64]


def _session_summary(s) -> Dict[str, Any]:
    return {
        "session_id": s.session_id,
        "project_id": s.project_id,
        "participant_label": s.participant_label,
        "topic": s.config.topic,
        "status": s.status.value,
        "phase": s.phase.value,
        "started_at": s.started_at,
        "ended_at": s.ended_at,
        "handoff_triggered": s.handoff_triggered,
        "join_url": _join_url(s.participant_token),
        "transcript_length": len(s.transcript),
    }


def _project_summary(store: TranscriptStore, p) -> Dict[str, Any]:
    return {
        **p.to_dict(),
        "session_count": store.session_count_for_project(p.project_id),
    }


def _parse_config(data: dict) -> InterviewConfig:
    return InterviewConfig.from_dict(data)


# --- Research projects ---


@interview_bp.route("/projects", methods=["POST"])
@require_auth
def create_project():
    try:
        data = request.get_json() or {}
        config = _parse_config(data)
        if not config.topic.strip():
            return jsonify({"success": False, "error": "topic is required"}), 400
        store = _get_store()
        project = store.create_project(
            config=config,
            name=data.get("name", ""),
            created_by=_created_by(),
        )
        return jsonify({"success": True, "project": _project_summary(store, project)})
    except Exception as exc:
        logger.error("create_project failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@interview_bp.route("/projects", methods=["GET"])
@require_auth
def list_projects():
    store = _get_store()
    projects = [_project_summary(store, p) for p in store.list_projects()]
    return jsonify({"success": True, "projects": projects})


@interview_bp.route("/projects/<project_id>", methods=["GET"])
@require_auth
def get_project(project_id):
    store = _get_store()
    project = store.get_project(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404
    return jsonify({
        "success": True,
        "project": _project_summary(store, project),
        "sessions": [_session_summary(s) for s in store.list_sessions(project_id)],
    })


@interview_bp.route("/projects/<project_id>", methods=["PATCH"])
@require_auth
def update_project(project_id):
    store = _get_store()
    project = store.get_project(project_id)
    if not project:
        return jsonify({"success": False, "error": "Project not found"}), 404

    data = request.get_json() or {}
    config = None
    if any(k in data for k in InterviewConfig.from_dict({}).to_dict()):
        merged = {**project.config.to_dict(), **data}
        config = _parse_config(merged)
        if not config.topic.strip():
            return jsonify({"success": False, "error": "topic is required"}), 400

    status = None
    if "status" in data:
        try:
            status = ProjectStatus(data["status"])
        except ValueError:
            return jsonify({"success": False, "error": "invalid status"}), 400

    updated = store.update_project(
        project_id,
        config=config,
        name=data.get("name"),
        status=status,
    )
    return jsonify({"success": True, "project": _project_summary(store, updated)})


@interview_bp.route("/projects/<project_id>/sessions", methods=["POST"])
@require_auth
def create_participant_session(project_id):
    try:
        store = _get_store()
        if not store.get_project(project_id):
            return jsonify({"success": False, "error": "Project not found"}), 404

        data = request.get_json() or {}
        session = store.create_session_for_project(
            project_id,
            created_by=_created_by(),
            participant_label=data.get("participant_label", ""),
        )
        if not session:
            return jsonify({"success": False, "error": "Could not create session"}), 500

        agent = _get_agent()
        opening = agent.start_session(session)
        store.save(session)

        return jsonify({
            "success": True,
            "session_id": session.session_id,
            "project_id": project_id,
            "participant_token": session.participant_token,
            "join_url": _join_url(session.participant_token),
            "opening_message": opening,
            "session": session.to_dict(include_scratchpad=True),
        })
    except Exception as exc:
        logger.error("create_participant_session failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@interview_bp.route("/projects/<project_id>/sessions", methods=["GET"])
@require_auth
def list_project_sessions(project_id):
    store = _get_store()
    if not store.get_project(project_id):
        return jsonify({"success": False, "error": "Project not found"}), 404
    sessions = [_session_summary(s) for s in store.list_sessions(project_id)]
    return jsonify({"success": True, "sessions": sessions})


# --- Legacy / flat session routes (backward compatible) ---


@interview_bp.route("/sessions", methods=["POST"])
@require_auth
def create_session_legacy():
    """Create project + first participant session in one step."""
    try:
        data = request.get_json() or {}
        config = _parse_config(data)
        if not config.topic.strip():
            return jsonify({"success": False, "error": "topic is required"}), 400

        store = _get_store()
        project = store.create_project(
            config=config,
            name=data.get("name", ""),
            created_by=_created_by(),
        )
        session = store.create_session_for_project(project.project_id, created_by=_created_by())
        assert session is not None

        agent = _get_agent()
        opening = agent.start_session(session)
        store.save(session)

        return jsonify({
            "success": True,
            "project_id": project.project_id,
            "session_id": session.session_id,
            "participant_token": session.participant_token,
            "join_url": _join_url(session.participant_token),
            "opening_message": opening,
            "session": session.to_dict(include_scratchpad=True),
            "project": _project_summary(store, project),
        })
    except Exception as exc:
        logger.error("create_session failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@interview_bp.route("/sessions", methods=["GET"])
@require_auth
def list_sessions():
    store = _get_store()
    project_id = request.args.get("project_id")
    sessions = [_session_summary(s) for s in store.list_sessions(project_id or None)]
    return jsonify({"success": True, "sessions": sessions})


@interview_bp.route("/sessions/<session_id>", methods=["GET"])
@require_auth
def get_session(session_id):
    store = _get_store()
    session = store.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found"}), 404
    project = store.get_project(session.project_id)
    return jsonify({
        "success": True,
        "session": session.to_dict(include_scratchpad=True),
        "join_url": _join_url(session.participant_token),
        "project": project.to_dict() if project else None,
    })


@interview_bp.route("/sessions/<session_id>/end", methods=["POST"])
@require_auth
def end_session_researcher(session_id):
    store = _get_store()
    session = store.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found"}), 404

    agent = _get_agent()
    agent.end_session(session, by_participant=False)

    if session.status == SessionStatus.COMPLETE and not session.insights:
        generator = _get_insight_generator()
        session.insights = generator.generate(session)

    store.save(session)
    return jsonify({"success": True, "session": session.to_dict(include_scratchpad=True)})


@interview_bp.route("/sessions/<session_id>/insights", methods=["GET"])
@require_auth
def get_insights(session_id):
    store = _get_store()
    session = store.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found"}), 404

    if not session.insights:
        generator = _get_insight_generator()
        session.insights = generator.generate(session)
        store.save(session)

    return jsonify({"success": True, "insights": session.insights})


@interview_bp.route("/sessions/<session_id>/export", methods=["GET"])
@require_auth
def export_insights(session_id):
    store = _get_store()
    session = store.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found"}), 404

    if not session.insights:
        generator = _get_insight_generator()
        session.insights = generator.generate(session)
        store.save(session)

    import json
    payload = json.dumps(session.insights, indent=2)
    return Response(
        payload,
        mimetype="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=interview-{session_id[:8]}-insights.json"
        },
    )


# --- Public participant routes ---


@interview_bp.route("/join/<token>", methods=["GET"])
def join_session(token):
    store = _get_store()
    session = store.get_by_token(token)
    if not session:
        return jsonify({"success": False, "error": "Invalid or expired interview link"}), 404

    has_history = len(session.transcript) > 0 and session.status.value in ("active", "pending")
    return jsonify({
        "success": True,
        "session_id": session.session_id,
        "project_id": session.project_id,
        "topic": session.config.topic,
        "time_limit_minutes": session.config.time_limit_minutes,
        "status": session.status.value,
        "phase": session.phase.value,
        "transcript": [e.to_dict() for e in session.transcript],
        "resuming": has_history and session.phase.value not in ("complete", "declined", "handoff"),
    })


@interview_bp.route("/join/<token>/message", methods=["POST"])
def participant_message(token):
    store = _get_store()
    session = store.get_by_token(token)
    if not session:
        return jsonify({"success": False, "error": "Invalid or expired interview link"}), 404

    if session.status in (SessionStatus.COMPLETE, SessionStatus.DECLINED, SessionStatus.HANDOFF):
        return jsonify({
            "success": False,
            "error": "This interview has ended",
            "status": session.status.value,
            "transcript": [e.to_dict() for e in session.transcript],
        }), 400

    data = request.get_json() or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "message is required"}), 400

    agent = _get_agent()
    reply, session = agent.handle_message(session, message)

    if session.status == SessionStatus.COMPLETE and not session.insights:
        generator = _get_insight_generator()
        session.insights = generator.generate(session)

    store.save(session)
    return jsonify({
        "success": True,
        "reply": reply,
        "phase": session.phase.value,
        "status": session.status.value,
        "handoff_triggered": session.handoff_triggered,
        "transcript": [e.to_dict() for e in session.transcript],
    })


@interview_bp.route("/join/<token>/end", methods=["POST"])
def participant_end(token):
    store = _get_store()
    session = store.get_by_token(token)
    if not session:
        return jsonify({"success": False, "error": "Invalid or expired interview link"}), 404

    agent = _get_agent()
    reply, session = agent.end_session(session, by_participant=True)

    if not session.insights:
        generator = _get_insight_generator()
        session.insights = generator.generate(session)

    store.save(session)
    return jsonify({
        "success": True,
        "reply": reply,
        "status": session.status.value,
        "insights_ready": session.insights is not None,
    })
