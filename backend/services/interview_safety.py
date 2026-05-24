"""
Deterministic safety checks and handoff triggers for text interviews.
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern

from ..utils.logging import get_logger

logger = get_logger("interview_safety")

HANDOFF_MESSAGE = (
    "Thank you for sharing that — it sounds like you may need help beyond what this "
    "research chat can provide. Please reach out to Halo support at support@halocollar.com "
    "or through the Halo app so our team can assist you directly. "
    "I'll stop the interview here. Take care."
)

AI_DISCLOSURE_MESSAGE = (
    "I'm an AI research assistant conducting this interview on behalf of the Halo product team. "
    "I'm not a human, but I'm here to listen and ask thoughtful questions about your experience."
)

DECLINE_MESSAGE = (
    "No problem at all — thanks for your time. You're free to close this page. "
    "We appreciate you considering it."
)


@dataclass
class SafetyResult:
    trigger_handoff: bool = False
    handoff_reason: Optional[str] = None
    ai_disclosure: bool = False
    refused_to_answer: bool = False


class InterviewSafety:
    """Regex/keyword-based safety analysis."""

    HANDOFF_PATTERNS: List[Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\baccount\s+(locked|hacked|compromised|suspended)\b",
            r"\b(can'?t|cannot)\s+log\s+in\b",
            r"\burgent\s+support\b",
            r"\bneed\s+(help|support)\s+now\b",
            r"\bharassment\b",
            r"\bthreat(en(?:ed|ing))?\b",
            r"\b(suicid(e|al)|self[\s-]?harm|hurt\s+myself)\b",
            r"\b(emergency|911|police)\b",
            r"\b(stalk(ed|ing)|abuse[ds]?)\b",
            r"\bsafety\s+risk\b",
        ]
    ]

    AI_DISCLOSURE_PATTERNS: List[Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"\bare\s+you\s+(a\s+)?human\b",
            r"\b(real\s+person|actual\s+person)\b",
            r"\b(is\s+this\s+a\s+bot|talking\s+to\s+a\s+bot)\b",
            r"\bwho\s+am\s+i\s+talking\s+to\b",
        ]
    ]

    REFUSAL_PATTERNS: List[Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"^(no|nope|pass|skip|prefer not|don'?t want to answer|rather not)\.?$",
            r"\b(not comfortable answering|no comment)\b",
        ]
    ]

    CONSENT_YES_PATTERNS: List[Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"^(yes|yeah|yep|yup|sure|ok|okay|agree|i agree|sounds good|go ahead|let'?s do it)\.?$",
            r"\b(i consent|happy to proceed|i'?m in)\b",
        ]
    ]

    CONSENT_NO_PATTERNS: List[Pattern] = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"^(no|nope|nah|decline|refuse|not interested)\.?$",
            r"\b(don'?t want to|do not want to)\b",
        ]
    ]

    def analyze_participant_message(self, text: str) -> SafetyResult:
        stripped = (text or "").strip()
        result = SafetyResult()

        for pattern in self.HANDOFF_PATTERNS:
            if pattern.search(stripped):
                result.trigger_handoff = True
                result.handoff_reason = "support_or_safety"
                return result

        for pattern in self.AI_DISCLOSURE_PATTERNS:
            if pattern.search(stripped):
                result.ai_disclosure = True
                return result

        for pattern in self.REFUSAL_PATTERNS:
            if pattern.search(stripped):
                result.refused_to_answer = True
                return result

        return result

    def is_consent_yes(self, text: str) -> bool:
        stripped = (text or "").strip()
        return any(p.search(stripped) for p in self.CONSENT_YES_PATTERNS)

    def is_consent_no(self, text: str) -> bool:
        stripped = (text or "").strip()
        return any(p.search(stripped) for p in self.CONSENT_NO_PATTERNS)

    def contains_banned_topic(self, text: str, banned_topics: List[str]) -> bool:
        lower = (text or "").lower()
        for topic in banned_topics:
            t = (topic or "").strip().lower()
            if t and t in lower:
                return True
        return False

    def filter_banned_from_output(self, text: str, banned_topics: List[str]) -> bool:
        """Return True if output is safe (no banned topics)."""
        return not self.contains_banned_topic(text, banned_topics)

    @staticmethod
    def is_single_question(text: str) -> bool:
        """Heuristic: at most one question mark and no multiple interrogatives."""
        if not text or not text.strip():
            return True
        question_marks = text.count("?")
        if question_marks > 1:
            return False
        if question_marks == 0:
            return True
        # Split on ? and check we don't have another question-like sentence after
        parts = text.split("?")
        trailing = parts[-1].strip() if len(parts) > 1 else ""
        if trailing and any(
            trailing.lower().startswith(w)
            for w in ("what", "how", "why", "when", "where", "who", "can you", "could you", "would you")
        ):
            return False
        return True
