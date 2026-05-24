"""
Post-session insight generation for text interviews.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.interview import InterviewSession
from ..utils.logging import get_logger

logger = get_logger("interview_insight_generator")

MOCK_LLM = os.getenv("INTERVIEW_MOCK_LLM", "").lower() in ("1", "true", "yes")

INSIGHTS_SYSTEM_PROMPT = """You are a user research analyst. Given an interview transcript, produce structured insights as JSON.

Rules:
- Base every claim on the transcript; include representative quotes as evidence.
- If uncertain, set confidence to "low" and note uncertainty.
- Do not invent facts not supported by the transcript.

Return ONLY valid JSON matching this schema:
{
  "key_takeaways": ["..."],
  "themes": [{"theme": "...", "evidence_quotes": ["..."], "confidence": "low|med|high"}],
  "pain_points": ["..."],
  "current_workarounds": ["..."],
  "jobs_to_be_done": ["..."],
  "moments_that_matter": ["..."],
  "opportunities": [{"opportunity": "...", "impact": "low|med|high", "notes": "..."}],
  "recommended_action": "...",
  "open_questions": ["..."],
  "risk_flags": ["privacy", "support_handoff", "other"]
}"""


class InsightGenerator:
    """Generates structured insights from completed interview sessions."""

    def __init__(self, claude_service=None):
        self.claude_service = claude_service

    def generate(self, session: InterviewSession) -> Dict[str, Any]:
        duration = self._duration_minutes(session)
        base = self._base_payload(session, duration)

        if MOCK_LLM or not self.claude_service or not session.transcript:
            base.update(self._mock_insights(session))
            return base

        transcript_text = self._format_transcript(session)
        prompt = f"""Topic: {session.config.topic}
Audience: {session.config.audience}
Hypothesis: {session.config.hypothesis or "none"}
Handoff triggered: {session.handoff_triggered}

Transcript:
{transcript_text}

Generate insights JSON."""

        try:
            response = self.claude_service.send_message(
                message=prompt,
                system_prompt=INSIGHTS_SYSTEM_PROMPT,
                max_tokens=2000,
                temperature=0.2,
            )
            parsed = self._parse_json(response.content)
            base.update(parsed)
        except Exception as exc:
            logger.warning("Insight generation failed: %s", exc)
            base.update(self._mock_insights(session))

        base["full_transcript"] = [e.to_dict() for e in session.transcript]
        return base

    def _base_payload(self, session: InterviewSession, duration: float) -> Dict[str, Any]:
        risk_flags: List[str] = []
        if session.handoff_triggered:
            risk_flags.append("support_handoff")
        return {
            "session_id": session.session_id,
            "topic": session.config.topic,
            "audience": session.config.audience,
            "duration_minutes": round(duration, 1),
            "consent": session.consent,
            "risk_flags": risk_flags,
            "full_transcript": [e.to_dict() for e in session.transcript],
        }

    def _mock_insights(self, session: InterviewSession) -> Dict[str, Any]:
        quotes = [
            e.text for e in session.transcript if e.role == "participant" and len(e.text) > 10
        ][:3]
        return {
            "key_takeaways": [
                f"Participant shared perspectives on {session.config.topic}",
            ],
            "themes": [
                {
                    "theme": "General experience",
                    "evidence_quotes": quotes or ["No detailed quotes captured"],
                    "confidence": "low" if len(quotes) < 2 else "med",
                }
            ],
            "pain_points": [],
            "current_workarounds": [],
            "jobs_to_be_done": [],
            "moments_that_matter": [],
            "opportunities": [],
            "recommended_action": "Review transcript and validate themes with additional interviews.",
            "open_questions": [f"Dig deeper into {session.config.topic} with follow-up sessions"],
        }

    def _duration_minutes(self, session: InterviewSession) -> float:
        if not session.started_at:
            return 0.0
        end = session.ended_at or datetime.now(timezone.utc).isoformat()
        try:
            start = datetime.fromisoformat(session.started_at.replace("Z", "+00:00"))
            finish = datetime.fromisoformat(end.replace("Z", "+00:00"))
            return max(0, (finish - start).total_seconds() / 60.0)
        except (ValueError, TypeError):
            return 0.0

    def _format_transcript(self, session: InterviewSession) -> str:
        lines = []
        for e in session.transcript:
            lines.append(f"{e.role}: {e.text}")
        return "\n".join(lines)

    def _parse_json(self, content: str) -> Dict[str, Any]:
        content = (content or "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
        return {}
