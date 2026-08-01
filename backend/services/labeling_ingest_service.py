"""
Process Make.com staging uploads into extracted-txt/<email>/<collar-sn>/.

Staging layout (input):
  staging/<email>/<gmail-message-id>/
    _meta.json
    raw/*.zip
    extracted/activity_session_*.txt

Processed layout (output):
  extracted-txt/<email>/<collar-sn>/activity_session_*.txt

Session trios (collar_collected / durations / user_reported) stay together.
Collar SN is read from *_collar_collected.txt when present; otherwise _unknown.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import boto3

from ..utils.config import Config
from ..utils.logging import get_logger
from .labeling_data_analyzer import (
    FILENAME_RE,
    UNKNOWN_COLLAR_SN,
    sanitize_collar_sn,
)

logger = get_logger("labeling_ingest_service")

COLLAR_SN_RE = re.compile(r"Collar SN:\s*(.+)$", re.I | re.M)


@dataclass
class StagingFile:
    key: str
    email: str
    message_id: str
    filename: str
    timestamp: str
    index: int
    kind: str
    size: int = 0


@dataclass
class ProcessReport:
    bucket: str
    staging_prefix: str
    output_prefix: str
    dry_run: bool
    cleared_output_keys: int = 0
    staging_batches: int = 0
    staging_files: int = 0
    sessions: int = 0
    copied: int = 0
    skipped_unchanged: int = 0
    unknown_sn_sessions: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    by_email: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    collar_sns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bucket": self.bucket,
            "staging_prefix": self.staging_prefix,
            "output_prefix": self.output_prefix,
            "dry_run": self.dry_run,
            "cleared_output_keys": self.cleared_output_keys,
            "staging_batches": self.staging_batches,
            "staging_files": self.staging_files,
            "sessions": self.sessions,
            "copied": self.copied,
            "skipped_unchanged": self.skipped_unchanged,
            "unknown_sn_sessions": self.unknown_sn_sessions,
            "errors": self.errors,
            "by_email": self.by_email,
            "collar_sns": self.collar_sns,
        }


class LabelingIngestService:
    """Copy staging extracted txts into collar-SN organized extracted-txt/."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        staging_prefix: Optional[str] = None,
        output_prefix: Optional[str] = None,
        region: Optional[str] = None,
        s3_client=None,
    ):
        self.bucket_name = bucket_name or Config.LABELING_S3_BUCKET_NAME
        self.staging_prefix = (
            staging_prefix or Config.LABELING_S3_STAGING_PREFIX or "staging/"
        ).rstrip("/") + "/"
        self.output_prefix = (
            output_prefix or Config.LABELING_S3_PREFIX or "extracted-txt/"
        ).rstrip("/") + "/"
        self.region = region or Config.S3_REGION or "us-east-1"
        self.s3_client = s3_client or boto3.client("s3", region_name=self.region)
        if not self.bucket_name:
            raise ValueError("LABELING_S3_BUCKET_NAME is not configured")

    def list_staging_extracted(self) -> List[StagingFile]:
        files: List[StagingFile] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.staging_prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                rel = key[len(self.staging_prefix) :] if key.startswith(self.staging_prefix) else key
                parts = [p for p in rel.split("/") if p]
                # <email>/<message_id>/extracted/<filename>
                if len(parts) != 4 or parts[2] != "extracted":
                    continue
                email, message_id, _extracted, filename = parts
                match = FILENAME_RE.match(filename)
                if not match:
                    continue
                files.append(
                    StagingFile(
                        key=key,
                        email=email.lower(),
                        message_id=message_id,
                        filename=filename,
                        timestamp=match.group("timestamp"),
                        index=int(match.group("index")),
                        kind=match.group("kind"),
                        size=int(obj.get("Size") or 0),
                    )
                )
        return files

    def staging_status(self) -> Dict[str, Any]:
        """Lightweight inventory of staging batches vs processed output."""
        staging_files = self.list_staging_extracted()
        batches = sorted({(f.email, f.message_id) for f in staging_files})
        by_email: Dict[str, int] = defaultdict(int)
        for f in staging_files:
            by_email[f.email] += 1

        output_count = 0
        output_emails = set()
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.output_prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if key.endswith("/") or not key.endswith(".txt"):
                    continue
                output_count += 1
                rel = key[len(self.output_prefix) :]
                parts = rel.split("/")
                if parts:
                    output_emails.add(parts[0])

        return {
            "bucket": self.bucket_name,
            "staging_prefix": self.staging_prefix,
            "output_prefix": self.output_prefix,
            "staging_batches": len(batches),
            "staging_extracted_files": len(staging_files),
            "staging_by_email": dict(sorted(by_email.items())),
            "staging_batch_ids": [
                {"email": e, "message_id": m} for e, m in batches
            ],
            "output_files": output_count,
            "output_emails": sorted(output_emails),
        }

    def _clear_output_prefix(self, dry_run: bool) -> int:
        keys: List[str] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.output_prefix):
            for obj in page.get("Contents", []) or []:
                if not obj["Key"].endswith("/"):
                    keys.append(obj["Key"])
        if dry_run or not keys:
            return len(keys)
        for i in range(0, len(keys), 1000):
            batch = keys[i : i + 1000]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
        return len(keys)

    def _get_text(self, key: str) -> str:
        body = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()
        return body.decode("utf-8", errors="replace")

    def _object_md5(self, key: str) -> Optional[str]:
        try:
            head = self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            etag = (head.get("ETag") or "").strip('"')
            # Multipart etags contain '-'
            if etag and "-" not in etag:
                return etag
            body = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()
            return hashlib.md5(body).hexdigest()
        except self.s3_client.exceptions.ClientError:
            return None
        except Exception:  # noqa: BLE001
            return None

    def process_staging(
        self,
        dry_run: bool = False,
        clear_output: bool = True,
    ) -> Dict[str, Any]:
        """
        Process all staging extracted files into extracted-txt/<email>/<collar-sn>/.

        Args:
            dry_run: Plan only; do not copy/delete.
            clear_output: Wipe extracted-txt/ before copying (clean reprocess).
        """
        report = ProcessReport(
            bucket=self.bucket_name,
            staging_prefix=self.staging_prefix,
            output_prefix=self.output_prefix,
            dry_run=dry_run,
        )

        if clear_output:
            report.cleared_output_keys = self._clear_output_prefix(dry_run=dry_run)
            logger.info(
                "Cleared %s keys under %s (dry_run=%s)",
                report.cleared_output_keys,
                self.output_prefix,
                dry_run,
            )

        files = self.list_staging_extracted()
        report.staging_files = len(files)
        report.staging_batches = len({(f.email, f.message_id) for f in files})

        # Group by labeler + session identity (timestamp+index).
        # If the same session appears in multiple Gmail messages, prefer the
        # lexicographically latest message_id's files.
        sessions: Dict[Tuple[str, str, int], List[StagingFile]] = defaultdict(list)
        for f in files:
            sessions[(f.email, f.timestamp, f.index)].append(f)

        report.sessions = len(sessions)
        sn_seen = set()
        by_email: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "email": "",
                "sessions": 0,
                "files_copied": 0,
                "collar_sns": set(),
                "message_ids": set(),
            }
        )

        for (email, timestamp, index), members in sorted(sessions.items()):
            # Resolve preferred member per kind from latest message_id
            by_kind: Dict[str, StagingFile] = {}
            for m in sorted(members, key=lambda x: x.message_id):
                by_kind[m.kind] = m
            chosen = list(by_kind.values())
            for m in chosen:
                by_email[email]["message_ids"].add(m.message_id)

            sn = None
            collar_member = by_kind.get("collar_collected")
            if collar_member:
                try:
                    text = self._get_text(collar_member.key)
                    match = COLLAR_SN_RE.search(text)
                    if match:
                        sn = sanitize_collar_sn(match.group(1))
                except Exception as exc:  # noqa: BLE001
                    report.errors.append(
                        {"key": collar_member.key, "error": f"read SN failed: {exc}"}
                    )
            if not sn:
                sn = UNKNOWN_COLLAR_SN
                report.unknown_sn_sessions += 1

            sn_seen.add(sn)
            by_email[email]["email"] = email
            by_email[email]["sessions"] += 1
            by_email[email]["collar_sns"].add(sn)

            for m in chosen:
                dest = f"{self.output_prefix}{email}/{sn}/{m.filename}"
                if dry_run:
                    report.copied += 1
                    by_email[email]["files_copied"] += 1
                    continue
                try:
                    src_md5 = self._object_md5(m.key)
                    dst_md5 = self._object_md5(dest)
                    if src_md5 and dst_md5 and src_md5 == dst_md5:
                        report.skipped_unchanged += 1
                        continue
                    self.s3_client.copy_object(
                        Bucket=self.bucket_name,
                        CopySource={"Bucket": self.bucket_name, "Key": m.key},
                        Key=dest,
                    )
                    report.copied += 1
                    by_email[email]["files_copied"] += 1
                except Exception as exc:  # noqa: BLE001
                    report.errors.append({"key": m.key, "dest": dest, "error": str(exc)})

        report.collar_sns = sorted(sn_seen)
        report.by_email = {
            email: {
                "email": stats["email"],
                "sessions": stats["sessions"],
                "files_copied": stats["files_copied"],
                "collar_sns": sorted(stats["collar_sns"]),
                "message_ids": sorted(stats["message_ids"]),
            }
            for email, stats in sorted(by_email.items())
        }
        return report.to_dict()
