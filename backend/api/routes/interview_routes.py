"""
API routes for AI 1:1 text interviews.
"""

from typing import Optional

from flask import Blueprint, jsonify, request, g, Response

from ...api.middleware.auth import require_auth
from ...models.interview import InterviewConfig, SessionStatus
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


@interview_bp.route("/sessions", methods=["POST"])
@require_auth
def create_session():
    try:
        data = request.get_json() or {}
        config = InterviewConfig.from_dict(data)
        if not config.topic.strip():
            return jsonify({"success": False, "error": "topic is required"}), 400

        store = _get_store()
        created_by = request.headers.get("X-Auth-Token", "researcher")[:64]
        session = store.create_session(config, created_by=created_by)

        agent = _get_agent()
        opening = agent.start_session(session)
        store.save(session)

        return jsonify({
            "success": True,
            "session_id": session.session_id,
            "participant_token": session.participant_token,
            "join_url": _join_url(session.participant_token),
            "opening_message": opening,
            "session": session.to_dict(include_scratchpad=True),
        })
    except Exception as exc:
        logger.error("create_session failed: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)}), 500


@interview_bp.route("/sessions", methods=["GET"])
@require_auth
def list_sessions():
    store = _get_store()
    sessions = []
    for s in store.list_sessions():
        sessions.append({
            "session_id": s.session_id,
            "topic": s.config.topic,
            "status": s.status.value,
            "phase": s.phase.value,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "handoff_triggered": s.handoff_triggered,
            "join_url": _join_url(s.participant_token),
            "transcript_length": len(s.transcript),
        })
    return jsonify({"success": True, "sessions": sessions})


@interview_bp.route("/sessions/<session_id>", methods=["GET"])
@require_auth
def get_session(session_id):
    store = _get_store()
    session = store.get_by_id(session_id)
    if not session:
        return jsonify({"success": False, "error": "Session not found"}), 404
    return jsonify({
        "success": True,
        "session": session.to_dict(include_scratchpad=True),
        "join_url": _join_url(session.participant_token),
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


@interview_bp.route("/join/<token>", methods=["GET"])
def join_session(token):
    store = _get_store()
    session = store.get_by_token(token)
    if not session:
        return jsonify({"success": False, "error": "Invalid or expired interview link"}), 404

    return jsonify({
        "success": True,
        "session_id": session.session_id,
        "topic": session.config.topic,
        "time_limit_minutes": session.config.time_limit_minutes,
        "status": session.status.value,
        "phase": session.phase.value,
        "transcript": [e.to_dict() for e in session.transcript],
    })


@interview_bp.route("/join/<token>/message", methods=["POST"])
def participant_message(token):
    store = _get_store()
    session = store.get_by_token(token)
    if not session:
        return jsonify({"success": False, "error": "Invalid or expired interview link"}), 404

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
