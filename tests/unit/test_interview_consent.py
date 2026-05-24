"""Tests for interview consent gating."""

import os
import pytest

os.environ["INTERVIEW_MOCK_LLM"] = "true"

from backend.models.interview import InterviewConfig, InterviewPhase, SessionStatus
from backend.models.interview import InterviewSession
from backend.services.interview_agent import InterviewAgent


@pytest.fixture
def agent():
    return InterviewAgent(claude_service=None)


@pytest.fixture
def session():
    config = InterviewConfig(topic="collar setup", audience="new pet owners")
    s = InterviewSession.create("test-project", config)
    agent = InterviewAgent(claude_service=None)
    agent.start_session(s)
    return s


def test_consent_no_declines(session, agent):
    reply, updated = agent.handle_message(session, "no")
    assert updated.phase == InterviewPhase.DECLINED
    assert updated.status == SessionStatus.DECLINED
    assert updated.consent["given"] is False
    assert "problem" in reply.lower() or "thanks" in reply.lower()


def test_consent_yes_advances_to_warmup(session, agent):
    reply, updated = agent.handle_message(session, "yes")
    assert updated.consent["given"] is True
    assert updated.phase == InterviewPhase.WARMUP
    assert "?" in reply or len(reply) > 10


def test_declined_session_no_exploration(session, agent):
    agent.handle_message(session, "no")
    reply, updated = agent.handle_message(session, "tell me about my experience")
    assert updated.phase == InterviewPhase.DECLINED
    assert "ended" in reply.lower() or "thank" in reply.lower()
