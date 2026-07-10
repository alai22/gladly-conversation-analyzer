"""
AI survey designer — chat-driven survey creation and editing.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..models.halo_survey import (
    ChatMessage,
    HaloSurvey,
    SurveySection,
    normalize_slug,
    validate_slug,
)
from ..services.halo_survey_prompts import DESIGNER_SYSTEM_PROMPT
from ..utils.logging import get_logger

logger = get_logger("halo_survey_designer")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    # Strip markdown fences if present
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find outermost JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _apply_survey_fields(existing: HaloSurvey, data: Dict[str, Any]) -> HaloSurvey:
    if data.get("title"):
        existing.title = data["title"].strip()
    if "description" in data:
        existing.description = data.get("description") or ""
    if "audience" in data:
        existing.audience = data.get("audience") or ""
    if data.get("slug") and not existing.slug_locked:
        slug = normalize_slug(data["slug"])
        if validate_slug(slug):
            existing.slug = slug
    if data.get("sections") is not None:
        existing.sections = [SurveySection.from_dict(s) for s in data["sections"]]
    existing.touch()
    return existing


def validate_survey_schema(survey: HaloSurvey) -> List[str]:
    errors: List[str] = []
    if not survey.title.strip():
        errors.append("Survey title is required")
    if not validate_slug(survey.slug):
        errors.append(f"Invalid slug: {survey.slug}")
    if not survey.sections:
        errors.append("Survey must have at least one section")
    seen_ids: set = set()
    for section in survey.sections:
        if not section.id:
            errors.append("Section missing id")
        for q in section.questions:
            if not q.id:
                errors.append("Question missing id")
            elif q.id in seen_ids:
                errors.append(f"Duplicate question id: {q.id}")
            else:
                seen_ids.add(q.id)
            if not q.text.strip():
                errors.append(f"Question {q.id} missing text")
    return errors


class HaloSurveyDesigner:
    def __init__(self, claude_service=None):
        self.claude_service = claude_service

    def chat(
        self,
        survey: HaloSurvey,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[HaloSurvey, str, List[str]]:
        """
        Process designer chat message. Returns (updated_survey, assistant_message, errors).
        """
        if not self.claude_service:
            return survey, "AI designer unavailable (Claude service not configured).", []

        current_json = json.dumps(
            {
                "title": survey.title,
                "description": survey.description,
                "audience": survey.audience,
                "slug": survey.slug,
                "sections": [s.to_dict() for s in survey.sections],
            },
            indent=2,
        )

        prompt = f"""Current survey definition:
{current_json}

User request:
{user_message}

Return the JSON response object as specified in your instructions."""

        history = list(conversation_history or [])
        try:
            response = self.claude_service.send_message(
                message=prompt,
                system_prompt=DESIGNER_SYSTEM_PROMPT,
                conversation_history=history,
                max_tokens=8192,
                temperature=0.3,
            )
            raw = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.error("Designer chat failed: %s", exc, exc_info=True)
            return survey, f"AI request failed: {exc}", [str(exc)]

        parsed = _extract_json(raw)
        if not parsed:
            return survey, raw or "Could not parse AI response. Please try rephrasing.", [
                "Failed to parse JSON from AI response"
            ]

        assistant_message = parsed.get("assistant_message") or "Survey updated."
        survey_data = parsed.get("survey")
        if not survey_data:
            return survey, assistant_message, ["AI response missing survey object"]

        updated = _apply_survey_fields(survey, survey_data)
        errors = validate_survey_schema(updated)
        if errors:
            return survey, f"{assistant_message}\n\nValidation errors: {'; '.join(errors)}", errors

        return updated, assistant_message, []

    def chat_messages_from_history(self, design_chat: List[ChatMessage]) -> List[Dict[str, str]]:
        result = []
        for msg in design_chat:
            role = "assistant" if msg.role == "assistant" else "user"
            result.append({"role": role, "content": msg.text})
        return result

    @staticmethod
    def make_chat_entry(role: str, text: str) -> ChatMessage:
        return ChatMessage(
            role=role,
            text=text,
            ts=datetime.now(timezone.utc).isoformat(),
        )
