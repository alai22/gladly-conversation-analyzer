"""
Store for research projects and participant interview sessions.
"""

import json
import os
from threading import Lock
from typing import Dict, List, Optional

from ..models.interview import (
    InterviewConfig,
    InterviewSession,
    ProjectStatus,
    ResearchProject,
)
from ..utils.logging import get_logger

logger = get_logger("interview_store")


class TranscriptStore:
    """In-memory store with optional JSON persistence."""

    def __init__(self, persist_path: Optional[str] = None):
        self._projects: Dict[str, ResearchProject] = {}
        self._sessions: Dict[str, InterviewSession] = {}
        self._token_index: Dict[str, str] = {}
        self._lock = Lock()
        self._persist_path = persist_path or os.getenv(
            "INTERVIEW_STORE_PATH", "data/interviews/store.json"
        )
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        legacy_path = os.getenv("INTERVIEW_STORE_PATH_LEGACY", "data/interviews/sessions.json")
        if not self._persist_path or not os.path.exists(self._persist_path):
            if os.path.exists(legacy_path):
                self._load_legacy(legacy_path)
            return
        try:
            with open(self._persist_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("projects", []):
                project = ResearchProject.from_dict(item)
                self._projects[project.project_id] = project
            for item in raw.get("sessions", []):
                session = InterviewSession.from_dict(item)
                self._sessions[session.session_id] = session
                self._token_index[session.participant_token] = session.session_id
            self._migrate_orphan_sessions()
            logger.info(
                "Loaded %d projects, %d sessions",
                len(self._projects),
                len(self._sessions),
            )
        except Exception as exc:
            logger.warning("Could not load interview store: %s", exc)

    def _load_legacy(self, path: str) -> None:
        """Migrate old sessions-only file into projects + sessions."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw.get("sessions", []):
                session = InterviewSession.from_dict(item)
                if not session.project_id:
                    project = ResearchProject.create(
                        config=session.config,
                        name=session.config.topic or "Legacy project",
                        created_by=session.created_by,
                    )
                    session.project_id = project.project_id
                    self._projects[project.project_id] = project
                self._sessions[session.session_id] = session
                self._token_index[session.participant_token] = session.session_id
            self._migrate_orphan_sessions()
            self._persist()
            logger.info("Migrated %d legacy sessions", len(self._sessions))
        except Exception as exc:
            logger.warning("Legacy migration failed: %s", exc)

    def _migrate_orphan_sessions(self) -> None:
        for session in list(self._sessions.values()):
            if session.project_id and session.project_id not in self._projects:
                self._projects[session.project_id] = ResearchProject(
                    project_id=session.project_id,
                    name=session.config.topic or "Recovered project",
                    config=InterviewConfig.from_dict(session.config.to_dict()),
                    created_by=session.created_by,
                )
            elif not session.project_id:
                project = ResearchProject.create(
                    config=session.config,
                    name=session.config.topic or "Legacy project",
                    created_by=session.created_by,
                )
                session.project_id = project.project_id
                self._projects[project.project_id] = project

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            payload = {
                "projects": [p.to_dict() for p in self._projects.values()],
                "sessions": [s.to_dict() for s in self._sessions.values()],
            }
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            logger.warning("Could not persist interview store: %s", exc)

    # --- Projects ---

    def create_project(
        self,
        config: InterviewConfig,
        name: str = "",
        created_by: str = "",
    ) -> ResearchProject:
        with self._lock:
            project = ResearchProject.create(config, name=name, created_by=created_by)
            self._projects[project.project_id] = project
            self._persist()
            return project

    def get_project(self, project_id: str) -> Optional[ResearchProject]:
        return self._projects.get(project_id)

    def list_projects(self) -> List[ResearchProject]:
        return sorted(
            self._projects.values(),
            key=lambda p: p.updated_at or p.created_at or p.project_id,
            reverse=True,
        )

    def update_project(
        self,
        project_id: str,
        config: Optional[InterviewConfig] = None,
        name: Optional[str] = None,
        status: Optional[ProjectStatus] = None,
    ) -> Optional[ResearchProject]:
        with self._lock:
            project = self._projects.get(project_id)
            if not project:
                return None
            if config is not None:
                project.config = config
            if name is not None:
                project.name = name.strip() or project.name
            if status is not None:
                project.status = status
            project.touch()
            self._persist()
            return project

    def session_count_for_project(self, project_id: str) -> int:
        return sum(1 for s in self._sessions.values() if s.project_id == project_id)

    # --- Participant sessions ---

    def create_session_for_project(
        self,
        project_id: str,
        created_by: str = "",
        participant_label: str = "",
    ) -> Optional[InterviewSession]:
        with self._lock:
            project = self._projects.get(project_id)
            if not project:
                return None
            config_snapshot = InterviewConfig.from_dict(project.config.to_dict())
            session = InterviewSession.create(
                project_id=project_id,
                config=config_snapshot,
                created_by=created_by,
                participant_label=participant_label,
            )
            self._sessions[session.session_id] = session
            self._token_index[session.participant_token] = session.session_id
            project.touch()
            self._persist()
            return session

    def get_by_id(self, session_id: str) -> Optional[InterviewSession]:
        return self._sessions.get(session_id)

    def get_by_token(self, token: str) -> Optional[InterviewSession]:
        session_id = self._token_index.get(token)
        if not session_id:
            return None
        return self._sessions.get(session_id)

    def list_sessions(self, project_id: Optional[str] = None) -> List[InterviewSession]:
        sessions = self._sessions.values()
        if project_id:
            sessions = [s for s in sessions if s.project_id == project_id]
        return sorted(
            sessions,
            key=lambda s: s.started_at or s.session_id,
            reverse=True,
        )

    def save(self, session: InterviewSession) -> InterviewSession:
        with self._lock:
            self._sessions[session.session_id] = session
            self._token_index[session.participant_token] = session.session_id
            self._persist()
            return session

    # Legacy helper — creates project + session in one step
    def create_session(self, config: InterviewConfig, created_by: str = "") -> InterviewSession:
        project = self.create_project(config, created_by=created_by)
        session = self.create_session_for_project(project.project_id, created_by=created_by)
        assert session is not None
        return session
