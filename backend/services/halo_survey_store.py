"""
JSON-backed store for Halo Survey definitions and responses.
"""

import json
import os
from threading import Lock
from typing import Dict, List, Optional

from ..models.halo_survey import (
    ChatMessage,
    HaloSurvey,
    SurveyResponse,
    SurveySection,
    SurveyStatus,
    normalize_slug,
    validate_slug,
)
from ..utils.logging import get_logger

logger = get_logger("halo_survey_store")


class HaloSurveyStore:
    def __init__(self, persist_path: Optional[str] = None):
        self._surveys: Dict[str, HaloSurvey] = {}
        self._slug_index: Dict[str, str] = {}
        self._responses: Dict[str, SurveyResponse] = {}
        self._lock = Lock()
        self._persist_path = persist_path or os.getenv(
            "HALO_SURVEY_STORE_PATH", "data/surveys/store.json"
        )
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if self._persist_path and os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                for item in raw.get("surveys", []):
                    survey = HaloSurvey.from_dict(item)
                    self._surveys[survey.survey_id] = survey
                    self._slug_index[survey.slug] = survey.survey_id
                for item in raw.get("responses", []):
                    resp = SurveyResponse.from_dict(item)
                    self._responses[resp.response_id] = resp
                logger.info("Loaded %d surveys, %d responses", len(self._surveys), len(self._responses))
            except Exception as exc:
                logger.warning("Could not load survey store: %s", exc)
        if not self._surveys:
            self._load_seeds()

    def _load_seeds(self) -> None:
        seed_dir = os.path.join(os.path.dirname(self._persist_path or "data/surveys/store.json"), "seeds")
        if not os.path.isdir(seed_dir):
            return
        for name in os.listdir(seed_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(seed_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                survey = HaloSurvey.from_dict(data)
                if survey.slug not in self._slug_index:
                    self._surveys[survey.survey_id] = survey
                    self._slug_index[survey.slug] = survey.survey_id
                    logger.info("Seeded survey: %s (%s)", survey.title, survey.slug)
            except Exception as exc:
                logger.warning("Could not load seed %s: %s", path, exc)
        if self._surveys:
            self._persist()

    def _persist(self) -> None:
        if not self._persist_path:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            payload = {
                "surveys": [s.to_dict() for s in self._surveys.values()],
                "responses": [r.to_dict() for r in self._responses.values()],
            }
            with open(self._persist_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            logger.warning("Could not persist survey store: %s", exc)

    # --- Surveys ---

    def create_survey(
        self,
        title: str,
        slug: str = "",
        description: str = "",
        audience: str = "",
        created_by: str = "",
        sections: Optional[List[SurveySection]] = None,
    ) -> HaloSurvey:
        with self._lock:
            normalized = normalize_slug(slug or title)
            if normalized in self._slug_index:
                raise ValueError(f"Slug already in use: {normalized}")
            if not validate_slug(normalized):
                raise ValueError(f"Invalid slug: {normalized}")
            survey = HaloSurvey.create(
                title=title,
                slug=normalized,
                description=description,
                audience=audience,
                created_by=created_by,
                sections=sections,
            )
            self._surveys[survey.survey_id] = survey
            self._slug_index[survey.slug] = survey.survey_id
            self._persist()
            return survey

    def get_survey(self, survey_id: str) -> Optional[HaloSurvey]:
        return self._surveys.get(survey_id)

    def get_by_slug(self, slug: str) -> Optional[HaloSurvey]:
        survey_id = self._slug_index.get(normalize_slug(slug))
        if not survey_id:
            return None
        return self._surveys.get(survey_id)

    def list_surveys(self) -> List[HaloSurvey]:
        return sorted(
            self._surveys.values(),
            key=lambda s: s.updated_at or s.created_at or s.survey_id,
            reverse=True,
        )

    def update_survey(self, survey: HaloSurvey) -> HaloSurvey:
        with self._lock:
            existing = self._surveys.get(survey.survey_id)
            if not existing:
                raise ValueError("Survey not found")
            if survey.slug != existing.slug:
                if existing.slug_locked:
                    raise ValueError("Slug is locked after publish")
                normalized = normalize_slug(survey.slug)
                if not validate_slug(normalized):
                    raise ValueError(f"Invalid slug: {normalized}")
                other_id = self._slug_index.get(normalized)
                if other_id and other_id != survey.survey_id:
                    raise ValueError(f"Slug already in use: {normalized}")
                del self._slug_index[existing.slug]
                survey.slug = normalized
                self._slug_index[normalized] = survey.survey_id
            survey.touch()
            self._surveys[survey.survey_id] = survey
            self._persist()
            return survey

    def delete_survey(self, survey_id: str) -> bool:
        with self._lock:
            survey = self._surveys.pop(survey_id, None)
            if not survey:
                return False
            self._slug_index.pop(survey.slug, None)
            self._responses = {
                rid: r for rid, r in self._responses.items() if r.survey_id != survey_id
            }
            self._persist()
            return True

    def publish_survey(self, survey_id: str) -> Optional[HaloSurvey]:
        with self._lock:
            survey = self._surveys.get(survey_id)
            if not survey:
                return None
            survey.status = SurveyStatus.ACTIVE
            survey.slug_locked = True
            survey.touch()
            self._persist()
            return survey

    def archive_survey(self, survey_id: str) -> Optional[HaloSurvey]:
        with self._lock:
            survey = self._surveys.get(survey_id)
            if not survey:
                return None
            survey.status = SurveyStatus.ARCHIVED
            survey.touch()
            self._persist()
            return survey

    def append_design_chat(self, survey_id: str, messages: List[ChatMessage]) -> Optional[HaloSurvey]:
        with self._lock:
            survey = self._surveys.get(survey_id)
            if not survey:
                return None
            survey.design_chat.extend(messages)
            survey.touch()
            self._persist()
            return survey

    def response_count(self, survey_id: str) -> int:
        return sum(1 for r in self._responses.values() if r.survey_id == survey_id)

    def response_count_by_status(self, survey_id: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for r in self._responses.values():
            if r.survey_id != survey_id:
                continue
            key = r.status.value if hasattr(r.status, "value") else str(r.status)
            counts[key] = counts.get(key, 0) + 1
        return counts

    # --- Responses ---

    def create_response(self, response: SurveyResponse) -> SurveyResponse:
        with self._lock:
            self._responses[response.response_id] = response
            self._persist()
            return response

    def get_response(self, response_id: str) -> Optional[SurveyResponse]:
        return self._responses.get(response_id)

    def save_response(self, response: SurveyResponse) -> SurveyResponse:
        with self._lock:
            self._responses[response.response_id] = response
            self._persist()
            return response

    def list_responses(self, survey_id: str) -> List[SurveyResponse]:
        return sorted(
            [r for r in self._responses.values() if r.survey_id == survey_id],
            key=lambda r: r.started_at or r.response_id,
            reverse=True,
        )

    def import_survey_from_dict(self, data: dict) -> HaloSurvey:
        """Import or update a survey from seed/dict (by survey_id or slug)."""
        with self._lock:
            survey = HaloSurvey.from_dict(data)
            existing = self._surveys.get(survey.survey_id)
            if not existing:
                existing = self.get_by_slug(survey.slug)
            if existing:
                survey.survey_id = existing.survey_id
                if existing.slug_locked:
                    survey.slug = existing.slug
            else:
                if survey.slug in self._slug_index:
                    raise ValueError(f"Slug already in use: {survey.slug}")
            self._surveys[survey.survey_id] = survey
            self._slug_index[survey.slug] = survey.survey_id
            self._persist()
            return survey
