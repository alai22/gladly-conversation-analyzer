"""
Interview session data models for AI 1:1 text interviews.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


class InterviewPhase(str, Enum):
    CONSENT = "consent"
    WARMUP = "warmup"
    EXPLORATION = "exploration"
    SYNTHESIS = "synthesis"
    WRAPUP = "wrapup"
    COMPLETE = "complete"
    HANDOFF = "handoff"
    DECLINED = "declined"


class SessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    HANDOFF = "handoff"
    DECLINED = "declined"


@dataclass
class InterviewConfig:
    topic: str
    audience: str
    time_limit_minutes: int = 15
    max_questions: int = 12
    banned_topics: List[str] = field(default_factory=list)
    compliance_notes: str = ""
    hypothesis: str = ""
    confidence_bar: int = 3
    allow_follow_up_recruitment: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewConfig":
        return cls(
            topic=data.get("topic", ""),
            audience=data.get("audience", ""),
            time_limit_minutes=int(data.get("time_limit_minutes", 15)),
            max_questions=int(data.get("max_questions", 12)),
            banned_topics=list(data.get("banned_topics") or []),
            compliance_notes=data.get("compliance_notes", ""),
            hypothesis=data.get("hypothesis", ""),
            confidence_bar=int(data.get("confidence_bar", 3)),
            allow_follow_up_recruitment=bool(data.get("allow_follow_up_recruitment", False)),
        )


@dataclass
class TranscriptEntry:
    role: str  # assistant | participant
    text: str
    ts: str

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "text": self.text, "ts": self.ts}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TranscriptEntry":
        return cls(role=data["role"], text=data["text"], ts=data["ts"])


@dataclass
class InterviewScratchpad:
    learned: List[str] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    questions_asked: List[str] = field(default_factory=list)
    synthesis_pending: bool = False
    remaining_minutes: float = 15.0
    remaining_questions: int = 12
    participant_energy: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewScratchpad":
        return cls(
            learned=list(data.get("learned") or []),
            unknowns=list(data.get("unknowns") or []),
            questions_asked=list(data.get("questions_asked") or []),
            synthesis_pending=bool(data.get("synthesis_pending", False)),
            remaining_minutes=float(data.get("remaining_minutes", 15)),
            remaining_questions=int(data.get("remaining_questions", 12)),
            participant_energy=data.get("participant_energy", "normal"),
        )


@dataclass
class InterviewSession:
    session_id: str
    participant_token: str
    config: InterviewConfig
    phase: InterviewPhase = InterviewPhase.CONSENT
    status: SessionStatus = SessionStatus.PENDING
    consent: Dict[str, Any] = field(default_factory=lambda: {"given": False, "timestamp": None})
    scratchpad: InterviewScratchpad = field(default_factory=InterviewScratchpad)
    transcript: List[TranscriptEntry] = field(default_factory=list)
    question_count: int = 0
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    handoff_triggered: bool = False
    insights: Optional[Dict[str, Any]] = None
    created_by: str = ""

    @classmethod
    def create(cls, config: InterviewConfig, created_by: str = "") -> "InterviewSession":
        session_id = str(uuid.uuid4())
        token = uuid.uuid4().hex
        scratchpad = InterviewScratchpad(
            remaining_minutes=float(config.time_limit_minutes),
            remaining_questions=config.max_questions,
            unknowns=[
                f"Participant fit for audience: {config.audience}",
                f"Experiences related to: {config.topic}",
            ],
        )
        return cls(
            session_id=session_id,
            participant_token=token,
            config=config,
            scratchpad=scratchpad,
            created_by=created_by,
        )

    def to_dict(self, include_scratchpad: bool = True) -> Dict[str, Any]:
        data = {
            "session_id": self.session_id,
            "participant_token": self.participant_token,
            "config": self.config.to_dict(),
            "phase": self.phase.value,
            "status": self.status.value,
            "consent": self.consent,
            "transcript": [e.to_dict() for e in self.transcript],
            "question_count": self.question_count,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "handoff_triggered": self.handoff_triggered,
            "insights": self.insights,
            "created_by": self.created_by,
        }
        if include_scratchpad:
            data["scratchpad"] = self.scratchpad.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterviewSession":
        return cls(
            session_id=data["session_id"],
            participant_token=data["participant_token"],
            config=InterviewConfig.from_dict(data["config"]),
            phase=InterviewPhase(data.get("phase", InterviewPhase.CONSENT.value)),
            status=SessionStatus(data.get("status", SessionStatus.PENDING.value)),
            consent=data.get("consent") or {"given": False, "timestamp": None},
            scratchpad=InterviewScratchpad.from_dict(data.get("scratchpad") or {}),
            transcript=[TranscriptEntry.from_dict(e) for e in (data.get("transcript") or [])],
            question_count=int(data.get("question_count", 0)),
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            handoff_triggered=bool(data.get("handoff_triggered", False)),
            insights=data.get("insights"),
            created_by=data.get("created_by", ""),
        )

    def append_transcript(self, role: str, text: str) -> None:
        self.transcript.append(
            TranscriptEntry(
                role=role,
                text=text,
                ts=datetime.now(timezone.utc).isoformat(),
            )
        )

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
