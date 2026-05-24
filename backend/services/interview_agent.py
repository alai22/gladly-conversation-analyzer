"""
Interview agent state machine orchestrator.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from ..models.interview import (
    InterviewConfig,
    InterviewPhase,
    InterviewSession,
    InterviewScratchpad,
    SessionStatus,
)
from ..services.interview_prompts import INTRO_MOCK, SYSTEM_PROMPT, build_developer_prompt
from ..services.interview_question_selector import QuestionSelector
from ..services.interview_safety import (
    AI_DISCLOSURE_MESSAGE,
    DECLINE_MESSAGE,
    HANDOFF_MESSAGE,
    InterviewSafety,
)
from ..utils.logging import get_logger

logger = get_logger("interview_agent")

MOCK_LLM = os.getenv("INTERVIEW_MOCK_LLM", "").lower() in ("1", "true", "yes")


class InterviewAgent:
    """Orchestrates interview phases, safety, and LLM phrasing."""

    def __init__(self, claude_service=None):
        self.claude_service = claude_service
        self.safety = InterviewSafety()
        self.selector = QuestionSelector(self.safety)

    def start_session(self, session: InterviewSession) -> str:
        """Generate opening message and append to transcript."""
        session.status = SessionStatus.ACTIVE
        session.started_at = session.utc_now_iso()
        session.phase = InterviewPhase.CONSENT

        if MOCK_LLM or not self.claude_service:
            msg = INTRO_MOCK.format(
                topic=session.config.topic,
                time_limit=session.config.time_limit_minutes,
            )
        else:
            template = self.selector.select(
                session.config, session.scratchpad, InterviewPhase.CONSENT
            )
            msg = self._generate_message(session, template.intent, InterviewPhase.CONSENT)

        session.append_transcript("assistant", msg)
        return msg

    def handle_message(self, session: InterviewSession, participant_text: str) -> Tuple[str, InterviewSession]:
        """Process participant message and return assistant reply."""
        participant_text = (participant_text or "").strip()
        if not participant_text:
            return "I didn't catch that — could you share a bit more?", session

        session.append_transcript("participant", participant_text)
        self._update_energy(session, participant_text)

        safety = self.safety.analyze_participant_message(participant_text)
        if safety.ai_disclosure:
            session.append_transcript("assistant", AI_DISCLOSURE_MESSAGE)
            return AI_DISCLOSURE_MESSAGE, session

        if safety.trigger_handoff:
            return self._trigger_handoff(session, safety.handoff_reason or "support_or_safety")

        if session.phase == InterviewPhase.CONSENT:
            return self._handle_consent(session, participant_text, safety.refused_to_answer)

        if session.phase in (InterviewPhase.COMPLETE, InterviewPhase.DECLINED, InterviewPhase.HANDOFF):
            msg = "This interview has ended. Thank you for your time."
            session.append_transcript("assistant", msg)
            return msg, session

        if safety.refused_to_answer:
            msg = self._acknowledge_refusal(session)
            session.append_transcript("assistant", msg)
            return msg, session

        self._update_budget(session)
        self._maybe_advance_phase(session)

        if session.phase == InterviewPhase.WRAPUP and session.question_count >= session.config.max_questions:
            return self._complete_session(session, "Thanks so much for sharing your perspective. That's all the questions I have — appreciate your time!")

        template = self.selector.select(
            session.config,
            session.scratchpad,
            session.phase,
            participant_text,
        )
        msg = self._generate_message(session, template.intent, session.phase)

        if not self.safety.filter_banned_from_output(msg, session.config.banned_topics):
            msg = "Let me rephrase — " + self._fallback_question(session)

        if session.phase in (InterviewPhase.EXPLORATION, InterviewPhase.SYNTHESIS, InterviewPhase.WARMUP):
            if "?" in msg or msg.strip().endswith("?"):
                session.question_count += 1
                session.scratchpad.remaining_questions = max(
                    0, session.config.max_questions - session.question_count
                )
            session.scratchpad.questions_asked.append(template.intent[:120])

        session.append_transcript("assistant", msg)
        return msg, session

    def end_session(self, session: InterviewSession, by_participant: bool = False) -> Tuple[str, InterviewSession]:
        if session.status in (SessionStatus.COMPLETE, SessionStatus.DECLINED, SessionStatus.HANDOFF):
            return "", session
        wrap_msg = (
            "Before we wrap up — is there anything else you think we should have asked about?"
            if by_participant and session.phase != InterviewPhase.WRAPUP
            else "Thank you for completing this interview. We really appreciate your insights."
        )
        if by_participant and session.phase not in (InterviewPhase.COMPLETE, InterviewPhase.WRAPUP):
            session.phase = InterviewPhase.WRAPUP
            session.append_transcript("assistant", wrap_msg)
            session.status = SessionStatus.COMPLETE
            session.phase = InterviewPhase.COMPLETE
            session.ended_at = session.utc_now_iso()
            return wrap_msg, session

        return self._complete_session(
            session,
            "Thank you for your time — this interview is now complete.",
        )

    def _handle_consent(
        self,
        session: InterviewSession,
        text: str,
        refused: bool,
    ) -> Tuple[str, InterviewSession]:
        if self.safety.is_consent_no(text) or refused:
            session.phase = InterviewPhase.DECLINED
            session.status = SessionStatus.DECLINED
            session.consent = {"given": False, "timestamp": session.utc_now_iso()}
            session.ended_at = session.utc_now_iso()
            session.append_transcript("assistant", DECLINE_MESSAGE)
            return DECLINE_MESSAGE, session

        if self.safety.is_consent_yes(text):
            session.consent = {"given": True, "timestamp": session.utc_now_iso()}
            session.phase = InterviewPhase.WARMUP
            template = self.selector.select(session.config, session.scratchpad, InterviewPhase.WARMUP)
            msg = self._generate_message(session, template.intent, InterviewPhase.WARMUP)
            session.append_transcript("assistant", msg)
            return msg, session

        msg = (
            "Just to confirm — are you okay to proceed with this short research interview? "
            "A simple yes or no works."
        )
        session.append_transcript("assistant", msg)
        return msg, session

    def _trigger_handoff(self, session: InterviewSession, reason: str) -> Tuple[str, InterviewSession]:
        session.phase = InterviewPhase.HANDOFF
        session.status = SessionStatus.HANDOFF
        session.handoff_triggered = True
        session.ended_at = session.utc_now_iso()
        session.append_transcript("assistant", HANDOFF_MESSAGE)
        return HANDOFF_MESSAGE, session

    def _acknowledge_refusal(self, session: InterviewSession) -> str:
        template = self.selector.select(
            session.config,
            session.scratchpad,
            session.phase,
        )
        if MOCK_LLM or not self.claude_service:
            return "No problem — we can skip that. " + self._fallback_question(session)
        return self._generate_message(
            session,
            f"Acknowledge they prefer not to answer, then ask a different question. {template.intent}",
            session.phase,
        )

    def _complete_session(self, session: InterviewSession, msg: str) -> Tuple[str, InterviewSession]:
        session.phase = InterviewPhase.COMPLETE
        session.status = SessionStatus.COMPLETE
        session.ended_at = session.utc_now_iso()
        session.append_transcript("assistant", msg)
        return msg, session

    def _update_energy(self, session: InterviewSession, text: str) -> None:
        words = len(text.split())
        if words <= 5:
            session.scratchpad.participant_energy = "terse"
        else:
            session.scratchpad.participant_energy = "normal"

    def _update_budget(self, session: InterviewSession) -> None:
        if session.started_at:
            try:
                started = datetime.fromisoformat(session.started_at.replace("Z", "+00:00"))
                elapsed = (datetime.now(timezone.utc) - started).total_seconds() / 60.0
                session.scratchpad.remaining_minutes = max(
                    0, session.config.time_limit_minutes - elapsed
                )
            except (ValueError, TypeError):
                pass

    def _maybe_advance_phase(self, session: InterviewSession) -> None:
        if session.phase == InterviewPhase.WARMUP and session.question_count >= 2:
            session.phase = InterviewPhase.EXPLORATION
        elif session.phase == InterviewPhase.EXPLORATION:
            if session.question_count > 0 and session.question_count % 4 == 0:
                session.phase = InterviewPhase.SYNTHESIS
                session.scratchpad.synthesis_pending = True
            elif session.scratchpad.remaining_questions <= 3:
                session.phase = InterviewPhase.WRAPUP
        elif session.phase == InterviewPhase.SYNTHESIS:
            session.scratchpad.synthesis_pending = False
            if session.scratchpad.remaining_questions <= 2:
                session.phase = InterviewPhase.WRAPUP
            else:
                session.phase = InterviewPhase.EXPLORATION

        if session.scratchpad.remaining_minutes <= 1 or session.scratchpad.remaining_questions <= 1:
            session.phase = InterviewPhase.WRAPUP

    def _generate_message(
        self,
        session: InterviewSession,
        template_intent: str,
        phase: InterviewPhase,
    ) -> str:
        if MOCK_LLM or not self.claude_service:
            return self._mock_message(session, template_intent, phase)

        developer = build_developer_prompt(
            session.config,
            session.scratchpad,
            phase,
            template_intent,
        )
        history = [
            {"role": "user" if e.role == "participant" else "assistant", "content": e.text}
            for e in session.transcript[-10:]
        ]
        prompt = "Generate the next interview turn as JSON."

        try:
            response = self.claude_service.send_message(
                message=prompt,
                system_prompt=SYSTEM_PROMPT + "\n\n" + developer,
                conversation_history=history,
                max_tokens=600,
                temperature=0.4,
            )
            parsed = self._parse_llm_json(response.content)
            msg = parsed.get("assistant_message", "")
            self._merge_scratchpad(session, parsed.get("scratchpad") or {})
            if msg and self.safety.is_single_question(msg):
                return msg.strip()
        except Exception as exc:
            logger.warning("LLM generation failed: %s", exc)

        return self._fallback_question(session)

    def _mock_message(
        self,
        session: InterviewSession,
        template_intent: str,
        phase: InterviewPhase,
    ) -> str:
        if phase == InterviewPhase.CONSENT:
            return INTRO_MOCK.format(
                topic=session.config.topic,
                time_limit=session.config.time_limit_minutes,
            )
        if phase == InterviewPhase.WARMUP:
            return f"To get started — how would you describe your role as it relates to {session.config.topic}?"
        if phase == InterviewPhase.SYNTHESIS:
            return "I want to make sure I understood — could you confirm if I summarized your main point correctly?"
        if phase == InterviewPhase.WRAPUP:
            return "Is there anything else you think we should have asked about?"
        return self._fallback_question(session)

    def _fallback_question(self, session: InterviewSession) -> str:
        return (
            f"Can you tell me more about your experience with {session.config.topic}? "
            "What stands out most to you?"
        )

    def _parse_llm_json(self, content: str) -> Dict[str, Any]:
        content = (content or "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                return json.loads(match.group())
        return {"assistant_message": content}

    def _merge_scratchpad(self, session: InterviewSession, updates: Dict[str, Any]) -> None:
        if "learned" in updates:
            for item in updates["learned"]:
                if item and item not in session.scratchpad.learned:
                    session.scratchpad.learned.append(str(item))
        if "unknowns" in updates:
            session.scratchpad.unknowns = [str(u) for u in updates["unknowns"]]
        if "phase" in updates:
            try:
                session.phase = InterviewPhase(updates["phase"])
            except ValueError:
                pass
