"""
In-memory transcript and session store for text interviews.
"""

import json
import os
from threading import Lock
from typing import Dict, List, Optional

from ..models.interview import InterviewConfig, InterviewSession
from ..utils.logging import get_logger

logger = get_logger("interview_store")


class TranscriptStore:
    """Stores interview sessions in memory with optional local JSON persistence."""

    def __init__(self, persist_path: Optional[str] = None):
        self._sessions: Dict[str, InterviewSession] = {}
        self._token_index: Dict[str, str] = {}
        self._lock = Lock()
        self._persist_path = persist_path or os.getenv(
            "INTERVIEW_STORE_PATH", "data/interviews/sessions.json"
        )
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._persist_path or not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("sessions", []):
                session = InterviewSession.from_dict(item)
                self._sessions[session.session_id] = session
                self._token_index[session.participant_token] = session.session_id
            logger.info("Loaded %d interview sessions from disk", len(self._sessions))
        except Exception as exc:
            logger.warning("Could not load interview sessions: %s", exc)

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            payload = {"sessions": [s.to_dict() for s in self._sessions.values()]}
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            logger.warning("Could not persist interview sessions: %s", exc)

    def create_session(self, config: InterviewConfig, created_by: str = "") -> InterviewSession:
        with self._lock:
            session = InterviewSession.create(config, created_by=created_by)
            self._sessions[session.session_id] = session
            self._token_index[session.participant_token] = session.session_id
            self._persist()
            return session

    def get_by_id(self, session_id: str) -> Optional[InterviewSession]:
        return self._sessions.get(session_id)

    def get_by_token(self, token: str) -> Optional[InterviewSession]:
        session_id = self._token_index.get(token)
        if not session_id:
            return None
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[InterviewSession]:
        return sorted(
            self._sessions.values(),
            key=lambda s: s.started_at or s.session_id,
            reverse=True,
        )

    def save(self, session: InterviewSession) -> InterviewSession:
        with self._lock:
            self._sessions[session.session_id] = session
            self._token_index[session.participant_token] = session.session_id
            self._persist()
            return session
