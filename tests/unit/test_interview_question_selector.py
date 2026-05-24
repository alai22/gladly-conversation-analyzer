"""Tests for question selector scoring."""

import os

os.environ["INTERVIEW_MOCK_LLM"] = "true"

from backend.models.interview import InterviewConfig, InterviewScratchpad, InterviewPhase
from backend.services.interview_question_selector import QuestionSelector


def test_wrapup_preferred_when_budget_low():
    config = InterviewConfig(topic="GPS accuracy", audience="dog owners", max_questions=10)
    scratchpad = InterviewScratchpad(remaining_questions=1, remaining_minutes=1)
    selector = QuestionSelector()
    template = selector.select(config, scratchpad, InterviewPhase.WRAPUP)
    assert template.category == "wrapup"


def test_consent_template_in_consent_phase():
    config = InterviewConfig(topic="beacons", audience="users")
    scratchpad = InterviewScratchpad()
    selector = QuestionSelector()
    template = selector.select(config, scratchpad, InterviewPhase.CONSENT)
    assert template.category == "consent"
