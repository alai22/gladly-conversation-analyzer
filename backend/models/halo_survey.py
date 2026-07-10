"""
Halo Survey data models: survey definitions and respondent responses.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import re
import uuid


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTI_SELECT = "multi_select"
    RATING = "rating"
    SHORT_TEXT = "short_text"
    LONG_TEXT = "long_text"
    RATING_WITH_TEXT = "rating_with_text"


class SurveyStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ResponseStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    INELIGIBLE = "ineligible"
    ABANDONED = "abandoned"


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_slug(slug: str) -> str:
    s = (slug or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def validate_slug(slug: str) -> bool:
    return bool(slug and SLUG_PATTERN.match(slug))


@dataclass
class Condition:
    question_id: str
    operator: str  # equals | not_equals | in | not_in | contains | not_contains
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["Condition"]:
        if not data:
            return None
        return cls(
            question_id=data.get("question_id", ""),
            operator=data.get("operator", "equals"),
            value=data.get("value"),
        )


@dataclass
class EndCondition(Condition):
    message: str = ""
    status: str = "ineligible"

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "message": self.message,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["EndCondition"]:
        if not data:
            return None
        return cls(
            question_id=data.get("question_id", ""),
            operator=data.get("operator", "equals"),
            value=data.get("value"),
            message=data.get("message", ""),
            status=data.get("status", "ineligible"),
        )


@dataclass
class SurveyQuestion:
    id: str
    type: QuestionType
    text: str
    required: bool = True
    options: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    help_text: str = ""
    placeholder: str = ""
    text_prompt: str = ""
    show_if: Optional[Condition] = None
    end_if: Optional[EndCondition] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, QuestionType) else self.type,
            "text": self.text,
            "required": self.required,
            "options": self.options,
            "labels": self.labels,
            "help_text": self.help_text,
            "placeholder": self.placeholder,
            "text_prompt": self.text_prompt,
        }
        if self.show_if:
            data["show_if"] = self.show_if.to_dict()
        if self.end_if:
            data["end_if"] = self.end_if.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyQuestion":
        qtype = data.get("type", QuestionType.SHORT_TEXT.value)
        if isinstance(qtype, QuestionType):
            qtype_val = qtype
        else:
            qtype_val = QuestionType(qtype)
        return cls(
            id=data.get("id", ""),
            type=qtype_val,
            text=data.get("text", ""),
            required=bool(data.get("required", True)),
            options=list(data.get("options") or []),
            labels=dict(data.get("labels") or {}),
            help_text=data.get("help_text", ""),
            placeholder=data.get("placeholder", ""),
            text_prompt=data.get("text_prompt", ""),
            show_if=Condition.from_dict(data.get("show_if")),
            end_if=EndCondition.from_dict(data.get("end_if")),
        )


@dataclass
class SurveySection:
    id: str
    title: str
    questions: List[SurveyQuestion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "questions": [q.to_dict() for q in self.questions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveySection":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            questions=[SurveyQuestion.from_dict(q) for q in (data.get("questions") or [])],
        )


@dataclass
class ChatMessage:
    role: str
    text: str
    ts: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "text": self.text, "ts": self.ts}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            role=data.get("role", "user"),
            text=data.get("text", ""),
            ts=data.get("ts", ""),
        )


def default_braze_url_template(slug: str) -> str:
    return (
        "https://insight.halocollar.com/s/"
        + slug
        + "?external_id={{${user_id}}}&utm_source=braze&utm_campaign=your_campaign"
    )


@dataclass
class HaloSurvey:
    survey_id: str
    slug: str
    title: str
    description: str = ""
    audience: str = ""
    status: SurveyStatus = SurveyStatus.DRAFT
    sections: List[SurveySection] = field(default_factory=list)
    design_chat: List[ChatMessage] = field(default_factory=list)
    braze_url_template: str = ""
    slug_locked: bool = False
    created_at: str = ""
    updated_at: str = ""
    created_by: str = ""

    @classmethod
    def create(
        cls,
        title: str,
        slug: str = "",
        description: str = "",
        audience: str = "",
        created_by: str = "",
        sections: Optional[List[SurveySection]] = None,
    ) -> "HaloSurvey":
        now = datetime.now(timezone.utc).isoformat()
        survey_id = str(uuid.uuid4())
        normalized = normalize_slug(slug or title or survey_id[:8])
        return cls(
            survey_id=survey_id,
            slug=normalized,
            title=(title or "Untitled Survey").strip(),
            description=description,
            audience=audience,
            status=SurveyStatus.DRAFT,
            sections=sections or [],
            braze_url_template=default_braze_url_template(normalized),
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def all_questions(self) -> List[SurveyQuestion]:
        questions: List[SurveyQuestion] = []
        for section in self.sections:
            questions.extend(section.questions)
        return questions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "survey_id": self.survey_id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "audience": self.audience,
            "status": self.status.value if isinstance(self.status, SurveyStatus) else self.status,
            "sections": [s.to_dict() for s in self.sections],
            "design_chat": [m.to_dict() for m in self.design_chat],
            "braze_url_template": self.braze_url_template or default_braze_url_template(self.slug),
            "slug_locked": self.slug_locked,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
        }

    def to_public_dict(self) -> Dict[str, Any]:
        """Survey definition for respondents — no admin metadata."""
        return {
            "survey_id": self.survey_id,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "audience": self.audience,
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HaloSurvey":
        status = data.get("status", SurveyStatus.DRAFT.value)
        if isinstance(status, SurveyStatus):
            status_val = status
        else:
            status_val = SurveyStatus(status)
        slug = data.get("slug", "")
        return cls(
            survey_id=data["survey_id"],
            slug=slug,
            title=data.get("title", ""),
            description=data.get("description", ""),
            audience=data.get("audience", ""),
            status=status_val,
            sections=[SurveySection.from_dict(s) for s in (data.get("sections") or [])],
            design_chat=[ChatMessage.from_dict(m) for m in (data.get("design_chat") or [])],
            braze_url_template=data.get("braze_url_template") or default_braze_url_template(slug),
            slug_locked=bool(data.get("slug_locked", False)),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            created_by=data.get("created_by", ""),
        )


@dataclass
class SurveyResponse:
    response_id: str
    survey_id: str
    slug: str
    status: ResponseStatus = ResponseStatus.IN_PROGRESS
    answers: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    completed_at: Optional[str] = None
    end_message: Optional[str] = None

    @classmethod
    def create(cls, survey_id: str, slug: str, metadata: Optional[Dict[str, Any]] = None) -> "SurveyResponse":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            response_id=str(uuid.uuid4()),
            survey_id=survey_id,
            slug=slug,
            status=ResponseStatus.IN_PROGRESS,
            answers={},
            metadata=metadata or {},
            started_at=now,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "survey_id": self.survey_id,
            "slug": self.slug,
            "status": self.status.value if isinstance(self.status, ResponseStatus) else self.status,
            "answers": self.answers,
            "metadata": self.metadata,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "end_message": self.end_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SurveyResponse":
        status = data.get("status", ResponseStatus.IN_PROGRESS.value)
        if isinstance(status, ResponseStatus):
            status_val = status
        else:
            status_val = ResponseStatus(status)
        return cls(
            response_id=data["response_id"],
            survey_id=data["survey_id"],
            slug=data.get("slug", ""),
            status=status_val,
            answers=dict(data.get("answers") or {}),
            metadata=dict(data.get("metadata") or {}),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at"),
            end_message=data.get("end_message"),
        )
