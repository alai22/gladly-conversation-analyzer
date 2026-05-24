"""Tests for interview fallback question phrasing."""

import os

os.environ["INTERVIEW_MOCK_LLM"] = "true"

from backend.models.interview import InterviewConfig, InterviewPhase, InterviewSession
from backend.services.interview_agent import InterviewAgent
from backend.services.interview_safety import InterviewSafety


def test_fallback_uses_topic_question_directly():
    agent = InterviewAgent(claude_service=None)
    config = InterviewConfig(
        topic="Which canine health goals matter to you?",
        audience="dog owners",
    )
    session = InterviewSession.create("proj", config)
    session.phase = InterviewPhase.EXPLORATION

    msg = agent._fallback_question(session)

    assert msg == "Which canine health goals matter to you?"
    assert msg.count("?") == 1
    assert "experience with" not in msg.lower()


def test_fallback_single_question_for_statement_topic():
    agent = InterviewAgent(claude_service=None)
    config = InterviewConfig(topic="GPS accuracy on walks", audience="pet owners")
    session = InterviewSession.create("proj", config)
    session.phase = InterviewPhase.EXPLORATION

    msg = agent._fallback_question(session)
    safety = InterviewSafety()

    assert safety.is_single_question(msg)
    assert "GPS accuracy" in msg
    assert "experience with" not in msg.lower()


def test_first_question_only_trims_multi_question_llm_output():
    text = (
        "Got it. What matters most for exercise? "
        "And how do you decide when they've had enough?"
    )
    trimmed = InterviewAgent._first_question_only(text)
    assert trimmed == "Got it. What matters most for exercise?"
    assert InterviewSafety.is_single_question(trimmed)
