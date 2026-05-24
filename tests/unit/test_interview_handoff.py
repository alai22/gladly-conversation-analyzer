"""Tests for handoff trigger detection."""

import os
import pytest

os.environ["INTERVIEW_MOCK_LLM"] = "true"

from backend.models.interview import InterviewConfig, InterviewPhase, SessionStatus
from backend.models.interview import InterviewSession
from backend.services.interview_agent import InterviewAgent
from backend.services.interview_safety import InterviewSafety


@pytest.fixture
def agent():
    return InterviewAgent(claude_service=None)


@pytest.fixture
def active_session():
    config = InterviewConfig(topic="app experience", audience="customers")
    s = InterviewSession.create("test-project", config)
    s.phase = InterviewPhase.EXPLORATION
    s.status = SessionStatus.ACTIVE
    s.consent = {"given": True, "timestamp": "2026-01-01T00:00:00+00:00"}
    return s


def test_handoff_keywords_trigger(active_session, agent):
    reply, updated = agent.handle_message(active_session, "I need urgent support, my account is locked")
    assert updated.handoff_triggered is True
    assert updated.phase == InterviewPhase.HANDOFF
    assert updated.status == SessionStatus.HANDOFF
    assert "support" in reply.lower()


def test_safety_detects_harassment():
    safety = InterviewSafety()
    result = safety.analyze_participant_message("Someone is harassing me online")
    assert result.trigger_handoff is True


def test_ai_disclosure_not_handoff(active_session, agent):
    reply, updated = agent.handle_message(active_session, "Are you a human?")
    assert updated.handoff_triggered is False
    assert "AI" in reply or "ai" in reply.lower()
