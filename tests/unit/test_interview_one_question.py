"""Tests for one-question-at-a-time validation."""

from backend.services.interview_safety import InterviewSafety


def test_single_question_passes():
    safety = InterviewSafety()
    assert safety.is_single_question("What was the last time you used the app?")
    assert safety.is_single_question("Thanks for sharing. That makes sense.")
    assert safety.is_single_question("Got it — can you tell me more?")


def test_multiple_questions_fail():
    safety = InterviewSafety()
    assert not safety.is_single_question("What do you think? And why?")
    assert not safety.is_single_question("How often does this happen? What do you do instead?")


def test_trailing_interrogative_fails():
    safety = InterviewSafety()
    text = "Thanks. What about the collar? How does that work?"
    assert not safety.is_single_question(text)
