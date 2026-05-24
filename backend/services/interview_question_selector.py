"""
Adaptive question template selection for text interviews.
"""

from dataclasses import dataclass
from typing import List, Optional

from ..models.interview import InterviewConfig, InterviewPhase, InterviewScratchpad
from ..services.interview_safety import InterviewSafety


@dataclass
class QuestionTemplate:
    id: str
    category: str
    intent: str
    template: str
    phases: List[InterviewPhase]


QUESTION_LIBRARY: List[QuestionTemplate] = [
    QuestionTemplate(
        "context_role",
        "context",
        "Confirm participant role/situation relative to audience",
        "Confirm whether they fit the target audience and their relevant role or situation.",
        [InterviewPhase.WARMUP],
    ),
    QuestionTemplate(
        "context_anchor",
        "context",
        "One anchoring context question",
        "Ask one question to anchor how they relate to the topic in their daily life.",
        [InterviewPhase.WARMUP],
    ),
    QuestionTemplate(
        "explore_last_time",
        "exploration",
        "Walk through a recent concrete example",
        "Ask them to walk through the last time they experienced something related to the topic.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_frequency",
        "exploration",
        "Quantify how often this comes up",
        "Ask how often this situation occurs and whether it is a big or small deal for them.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_impact",
        "exploration",
        "Understand impact on their goals",
        "Ask about the impact on their goals, workflow, or peace of mind.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_alternatives",
        "exploration",
        "Learn what they do instead today",
        "Ask what they currently do instead or what workarounds they use.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_decision_criteria",
        "exploration",
        "Understand decision criteria",
        "Ask what would matter most if they were choosing between options.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_trust",
        "exploration",
        "Probe trust and comprehension",
        "Ask what helps them trust or understand a product or feature in this area.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "explore_good_look_like",
        "exploration",
        "Ideal outcome",
        "Ask what 'good' would look like for them in this area.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "clarify_terms",
        "exploration",
        "Clarify unclear terms from last response",
        "Ask them to clarify something ambiguous from their last answer.",
        [InterviewPhase.EXPLORATION],
    ),
    QuestionTemplate(
        "synthesis_check",
        "synthesis",
        "Reflect back and validate interpretation",
        "Reflect back what you heard and ask if you got it right.",
        [InterviewPhase.SYNTHESIS],
    ),
    QuestionTemplate(
        "wrapup_anything_else",
        "wrapup",
        "Final open question",
        "Ask if there is anything else we should have asked about this topic.",
        [InterviewPhase.WRAPUP],
    ),
    QuestionTemplate(
        "wrapup_followup",
        "wrapup",
        "Permission for follow-up",
        "If allowed, ask permission for a brief follow-up or future research contact.",
        [InterviewPhase.WRAPUP],
    ),
    QuestionTemplate(
        "consent",
        "consent",
        "Intro and consent request",
        "Deliver friendly intro: AI assistant for Halo Collar, topic, time expectation, and ask if they are happy to proceed. Do not promise confidentiality or that you will not sell anything.",
        [InterviewPhase.CONSENT],
    ),
]


class QuestionSelector:
    """Scores candidate templates and picks the best next question intent."""

    def __init__(self, safety: Optional[InterviewSafety] = None):
        self.safety = safety or InterviewSafety()

    def select(
        self,
        config: InterviewConfig,
        scratchpad: InterviewScratchpad,
        phase: InterviewPhase,
        last_participant_message: str = "",
    ) -> QuestionTemplate:
        candidates = [t for t in QUESTION_LIBRARY if phase in t.phases]
        if not candidates:
            candidates = [t for t in QUESTION_LIBRARY if InterviewPhase.EXPLORATION in t.phases]

        scored = []
        for template in candidates:
            if self.safety.contains_banned_topic(template.intent, config.banned_topics):
                continue
            if self.safety.contains_banned_topic(template.template, config.banned_topics):
                continue
            score = self._score(template, config, scratchpad, last_participant_message)
            scored.append((score, template))

        if not scored:
            return candidates[0] if candidates else QUESTION_LIBRARY[0]

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _score(
        self,
        template: QuestionTemplate,
        config: InterviewConfig,
        scratchpad: InterviewScratchpad,
        last_participant_message: str,
    ) -> float:
        score = 0.0

        # Information gain: prefer templates addressing unknowns
        for unknown in scratchpad.unknowns:
            if any(word in unknown.lower() for word in template.category.split("_")):
                score += 2.0

        # Coverage by category
        category_boost = {
            "context": 3.0 if scratchpad.remaining_questions == config.max_questions else 0.5,
            "exploration": 2.0 + (config.confidence_bar * 0.3),
            "synthesis": 2.5 if scratchpad.synthesis_pending else 0.5,
            "wrapup": 3.0 if scratchpad.remaining_questions <= 2 else 0.0,
            "consent": 10.0,
        }
        score += category_boost.get(template.category, 1.0)

        # Recency penalty
        if template.id in [q[:20] for q in scratchpad.questions_asked]:
            score -= 5.0
        for asked in scratchpad.questions_asked:
            if template.intent.lower() in asked.lower():
                score -= 3.0

        # Terse participant: prefer shorter-impact questions
        if scratchpad.participant_energy == "terse":
            if template.category in ("explore_impact", "explore_frequency"):
                score += 1.5
            if template.category == "explore_last_time":
                score -= 1.0

        # Clarify if last message was short/vague
        if last_participant_message and len(last_participant_message.split()) < 8:
            if template.id == "clarify_terms":
                score += 4.0

        # Time/question budget
        if scratchpad.remaining_questions <= 3 and template.category == "wrapup":
            score += 5.0
        if scratchpad.remaining_minutes <= 3 and template.category in ("synthesis", "wrapup"):
            score += 3.0

        # Hypothesis relevance
        if config.hypothesis and config.hypothesis.lower() in template.intent.lower():
            score += 1.0

        return score
