"""Tests for banned topic enforcement."""

import os
import pytest

os.environ["INTERVIEW_MOCK_LLM"] = "true"

from backend.models.interview import InterviewConfig, InterviewScratchpad, InterviewPhase
from backend.services.interview_question_selector import QuestionSelector
from backend.services.interview_safety import InterviewSafety


@pytest.fixture
def safety():
    return InterviewSafety()


@pytest.fixture
def selector():
    return QuestionSelector()


def test_banned_topic_detected_in_text(safety):
    assert safety.contains_banned_topic("Let's talk about pricing plans", ["pricing"])
    assert not safety.contains_banned_topic("Let's talk about setup", ["pricing"])


def test_banned_output_filtered(safety):
    assert not safety.filter_banned_from_output("How is setup going?", ["competitors"])
    assert not safety.filter_banned_from_output("Do you use a competitor product?", ["competitors"])


def test_selector_skips_banned_templates(selector):
    config = InterviewConfig(
        topic="onboarding",
        audience="new users",
        banned_topics=["competitor", "pricing"],
    )
    scratchpad = InterviewScratchpad()
    template = selector.select(config, scratchpad, InterviewPhase.EXPLORATION)
    combined = (template.intent + template.template).lower()
    assert "competitor" not in combined
    assert "pricing" not in combined
