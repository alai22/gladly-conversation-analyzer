"""Tests for research project / participant session store."""

import json

import pytest

from backend.models.interview import InterviewConfig, InterviewSession
from backend.services.interview_store import TranscriptStore


@pytest.fixture
def store_path(tmp_path):
    return str(tmp_path / "store.json")


def test_create_project_and_session(store_path):
    store = TranscriptStore(persist_path=store_path)
    config = InterviewConfig(topic="GPS accuracy", audience="Halo owners")
    project = store.create_project(config, name="GPS study", created_by="researcher")

    session = store.create_session_for_project(
        project.project_id,
        created_by="researcher",
        participant_label="Participant A",
    )
    assert session is not None
    assert session.project_id == project.project_id
    assert session.participant_label == "Participant A"
    assert session.config.topic == "GPS accuracy"
    assert store.session_count_for_project(project.project_id) == 1


def test_project_edit_does_not_change_existing_session_config(store_path):
    store = TranscriptStore(persist_path=store_path)
    config = InterviewConfig(topic="Original topic", audience="owners", time_limit_minutes=15)
    project = store.create_project(config, name="Study")
    session = store.create_session_for_project(project.project_id)
    assert session is not None

    updated_config = InterviewConfig(
        topic="Updated topic",
        audience="owners",
        time_limit_minutes=30,
    )
    store.update_project(project.project_id, config=updated_config)

    unchanged = store.get_by_id(session.session_id)
    assert unchanged.config.topic == "Original topic"
    assert unchanged.config.time_limit_minutes == 15

    new_session = store.create_session_for_project(project.project_id)
    assert new_session.config.topic == "Updated topic"
    assert new_session.config.time_limit_minutes == 30


def test_legacy_sessions_migrate_to_projects(store_path, tmp_path, monkeypatch):
    legacy_path = str(tmp_path / "sessions.json")
    config = InterviewConfig(topic="Legacy topic", audience="users")
    session = InterviewSession.create("", config, created_by="legacy")
    legacy_data = session.to_dict()
    legacy_data.pop("project_id", None)
    with open(legacy_path, "w", encoding="utf-8") as f:
        json.dump({"sessions": [legacy_data]}, f)

    monkeypatch.setenv("INTERVIEW_STORE_PATH_LEGACY", legacy_path)
    store = TranscriptStore(persist_path=store_path)

    assert len(store.list_projects()) == 1
    loaded = store.get_by_id(session.session_id)
    assert loaded.project_id
    assert store.get_project(loaded.project_id) is not None


def test_orphan_session_recovered_with_existing_project_id(store_path):
    config = InterviewConfig(topic="Orphan", audience="users")
    project_id = "fixed-project-id"
    session = InterviewSession.create(project_id, config)
    store = TranscriptStore(persist_path=store_path)
    store._sessions[session.session_id] = session
    store._token_index[session.participant_token] = session.session_id
    store._migrate_orphan_sessions()

    project = store.get_project(project_id)
    assert project is not None
    assert project.project_id == project_id
