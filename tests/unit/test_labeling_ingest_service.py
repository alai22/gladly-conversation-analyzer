"""Unit tests for labeling staging → extracted-txt ingest helpers."""

from backend.services.labeling_data_analyzer import FILENAME_RE, sanitize_collar_sn
from backend.services.labeling_ingest_service import LabelingIngestService


def test_sanitize_and_filename_helpers():
    assert sanitize_collar_sn("24h4290312rt") == "24h4290312rt"
    assert sanitize_collar_sn("") == "_unknown"
    m = FILENAME_RE.match(
        "activity_session_2026-05-14T05:26:37_0_collar_collected.txt"
    )
    assert m is not None
    assert m.group("kind") == "collar_collected"


def test_staging_status_requires_bucket(monkeypatch):
    monkeypatch.setattr(
        "backend.services.labeling_ingest_service.Config.LABELING_S3_BUCKET_NAME",
        None,
        raising=False,
    )
    try:
        LabelingIngestService(bucket_name=None)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "LABELING_S3_BUCKET_NAME" in str(exc)
