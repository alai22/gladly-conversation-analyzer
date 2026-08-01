"""Unit tests for labeling staging → extracted-txt ingest helpers."""

from backend.services.labeling_data_analyzer import FILENAME_RE, sanitize_collar_sn
from backend.services.labeling_ingest_service import (
    LabelingIngestService,
    forward_body_from_meta,
    looks_like_labeler_email,
    normalize_labeler_email,
    parse_original_from_forward_body,
    resolve_forward_labeler,
)


def test_sanitize_and_filename_helpers():
    assert sanitize_collar_sn("24h4290312rt") == "24h4290312rt"
    assert sanitize_collar_sn("") == "_unknown"
    m = FILENAME_RE.match(
        "activity_session_2026-05-14T05:26:37_0_collar_collected.txt"
    )
    assert m is not None
    assert m.group("kind") == "collar_collected"
    assert m.group("family") == "activity"
    g = FILENAME_RE.match("gps_session_2025-10-10T12:13:33_0_durations.txt")
    assert g is not None
    assert g.group("family") == "gps"


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


def test_looks_like_labeler_email():
    assert looks_like_labeler_email("lindseyw7485@gmail.com")
    assert not looks_like_labeler_email("_forwards")
    assert not looks_like_labeler_email("adrian lai")
    assert not looks_like_labeler_email("24h4290093rt")


def test_parse_original_from_forward_body():
    body = """
---------- Forwarded message ---------
From: Lindsey Delaney <lindseyw7485@gmail.com>
Date: Wed, May 27, 2026
Subject: HALO | Logs for Machine Learning
To: ai_logs@halocollar.com

30 seconds of lying.
"""
    assert parse_original_from_forward_body(body) == "lindseyw7485@gmail.com"


def test_resolve_forward_labeler_prefers_override_then_meta_then_body():
    meta = {"Original Labeler Email Address": "meta@example.com"}
    body = "Forwarded message\nFrom: Body User <body@example.com>\n"
    email, source = resolve_forward_labeler(
        meta, body=body, override="override@example.com"
    )
    assert email == "override@example.com"
    assert source == "override"

    email, source = resolve_forward_labeler(meta, body=body)
    assert email == "meta@example.com"
    assert source == "meta"

    email, source = resolve_forward_labeler({}, body=body)
    assert email == "body@example.com"
    assert source == "body"

    email, source = resolve_forward_labeler({"Labeler Email Address": "alai@halocollar.com"})
    assert email is None
    assert source == "none"


def test_resolve_forward_labeler_from_meta_email_body_field():
    meta = {
        "Labeler Email Address": "alai@halocollar.com",
        "Email Body": (
            "---------- Forwarded message ---------\r\n"
            "From: Brandon Rivera <brivera4459@gmail.com>\r\n"
            "Date: Thu, May 28, 2026\r\n"
            "Subject: HALO | Logs for Machine Learning\r\n"
        ),
    }
    assert forward_body_from_meta(meta).startswith("---------- Forwarded")
    email, source = resolve_forward_labeler(meta)
    assert email == "brivera4459@gmail.com"
    assert source == "meta.body"


def test_normalize_labeler_email():
    assert normalize_labeler_email("Lindsey <lindseyw7485@gmail.com>") == (
        "lindseyw7485@gmail.com"
    )
    assert normalize_labeler_email("not-an-email") is None


class _FakeS3:
    def __init__(self, objects=None):
        self.objects = dict(objects or {})
        self.copies = []
        self.puts = []

    def get_paginator(self, _name):
        client = self

        class _Pager:
            def paginate(self, Bucket=None, Prefix=""):  # noqa: N803
                keys = sorted(k for k in client.objects if k.startswith(Prefix))
                yield {
                    "Contents": [
                        {"Key": k, "Size": len(client.objects[k])} for k in keys
                    ]
                }

        return _Pager()

    def get_object(self, Bucket=None, Key=None):  # noqa: N803
        class _Body:
            def __init__(self, data):
                self._data = data

            def read(self):
                return self._data

        return {"Body": _Body(self.objects[Key])}

    def put_object(self, Bucket=None, Key=None, Body=None, ContentType=None):  # noqa: N803
        data = Body if isinstance(Body, (bytes, bytearray)) else str(Body).encode()
        self.objects[Key] = bytes(data)
        self.puts.append(Key)

    def copy_object(self, Bucket=None, CopySource=None, Key=None):  # noqa: N803
        src = CopySource["Key"]
        self.objects[Key] = self.objects[src]
        self.copies.append((src, Key))

    def head_object(self, Bucket=None, Key=None):  # noqa: N803
        import hashlib

        body = self.objects[Key]
        return {"ETag": f'"{hashlib.md5(body).hexdigest()}"'}


def test_list_staging_skips_forwards_and_display_names():
    s3 = _FakeS3(
        {
            "staging/_forwards/abc/extracted/activity_session_2026-05-01T15:09:55_0_collar_collected.txt": b"x",
            "staging/adrian lai/abc/extracted/activity_session_2026-05-01T15:09:55_0_collar_collected.txt": b"x",
            "staging/lindseyw7485@gmail.com/abc/extracted/activity_session_2026-05-01T15:09:55_0_collar_collected.txt": b"y",
        }
    )
    svc = LabelingIngestService(
        bucket_name="test-bucket",
        staging_prefix="staging/",
        output_prefix="extracted-txt/",
        s3_client=s3,
    )
    files = svc.list_staging_extracted()
    assert len(files) == 1
    assert files[0].email == "lindseyw7485@gmail.com"


def test_promote_forwards_copies_and_records_attribution():
    import json

    meta = json.dumps(
        {
            "Message ID": "abc123",
            "Email Subject": "Fwd: HALO",
            "Labeler Email Address": "alai@halocollar.com",
            "Attachment Filename": "logs.zip",
            "Email Body": (
                "---------- Forwarded message ---------\n"
                "From: Lindsey <lindseyw7485@gmail.com>\n\nhi\n"
            ),
        }
    ).encode()
    s3 = _FakeS3(
        {
            "staging/_forwards/abc123/_meta.json": meta,
            "staging/_forwards/abc123/logs.zip": b"ZIP",
            "staging/_forwards/abc123/extracted/activity_session_2026-05-01T15:09:55_0_collar_collected.txt": b"Collar SN: 24h4290093rt\n",
        }
    )
    svc = LabelingIngestService(
        bucket_name="test-bucket",
        staging_prefix="staging/",
        output_prefix="extracted-txt/",
        s3_client=s3,
    )
    report = svc.promote_forwards(dry_run=False)
    assert len(report["promoted"]) == 1
    assert report["promoted"][0]["labeler_email"] == "lindseyw7485@gmail.com"
    assert report["promoted"][0]["labeler_resolved_from"] == "meta.body"

    dest_meta = json.loads(
        s3.objects["staging/lindseyw7485@gmail.com/abc123/_meta.json"].decode()
    )
    assert dest_meta["Labeler Email Address"] == "lindseyw7485@gmail.com"
    assert dest_meta["attribution"]["forwarded"] is True
    assert dest_meta["attribution"]["forwarder"] == "alai@halocollar.com"
    assert (
        "staging/lindseyw7485@gmail.com/abc123/raw/logs.zip" in s3.objects
    )
    assert (
        "staging/lindseyw7485@gmail.com/abc123/extracted/"
        "activity_session_2026-05-01T15:09:55_0_collar_collected.txt"
        in s3.objects
    )
    # Quarantine retained + ledger written
    assert "staging/_forwards/abc123/_meta.json" in s3.objects
    ledger = json.loads(s3.objects["staging/_forwards/_attributions.json"].decode())
    assert ledger["entries"][0]["labeler_email"] == "lindseyw7485@gmail.com"

    pending = svc.pending_forwards()
    assert pending["pending_count"] == 0
    assert len(pending["already_promoted"]) == 1

    # Second promote is a no-op skip
    again = svc.promote_forwards(dry_run=False)
    assert again["promoted"] == []
    assert again["skipped"][0]["reason"] == "already_promoted"
