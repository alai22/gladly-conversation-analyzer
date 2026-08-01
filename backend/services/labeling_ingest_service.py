"""
Process Make.com staging uploads into extracted-txt/<email>/<collar-sn>/.

Staging layout (input):
  staging/<email>/<gmail-message-id>/
    _meta.json
    raw/*.zip
    extracted/activity_session_*.txt   # posture model
    extracted/gps_session_*.txt        # indoor/outdoor model

Forward quarantine (not a labeler; skipped by process_staging):
  staging/_forwards/<gmail-message-id>/
    _meta.json
    email_body.txt          # optional; original From may instead live in _meta
    raw/*.zip or *.zip
    extracted/...           # optional if Make already unzipped

  Original labeler is parsed from email_body.txt and/or _meta "Email Body".

Promote forwards → normal staging/<labeler>/<id>/ with attribution in _meta,
then process_staging aggregates like any other batch.

Processed layout (output):
  extracted-txt/<email>/<collar-sn>/activity_session_*.txt
  extracted-txt/<email>/<collar-sn>/gps_session_*.txt

Session trios (collar_collected / durations / user_reported) stay together.
Collar SN is read from *_collar_collected.txt when present; otherwise _unknown.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any, Dict, List, Optional, Set, Tuple

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

# Quarantine / bookkeeping folders — never treat as labeler emails.
RESERVED_STAGING_FOLDERS = frozenset({"_forwards", "_promoted", "_tmp"})

FORWARDS_FOLDER = "_forwards"
FORWARDS_LEDGER_KEY_SUFFIX = "_forwards/_attributions.json"
# S3 copy volume where UI may auto-promote on page load (~few seconds).
AUTO_PROMOTE_MAX_KEYS = 80

# Gmail / Apple Mail forward bodies.
FORWARDED_FROM_RE = re.compile(
    r"(?:^|\n)From:\s*(.+?)(?:\n|$)",
    re.I,
)
EMAIL_IN_TEXT_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def looks_like_labeler_email(folder: str) -> bool:
    """True if staging path segment should be treated as a labeler folder."""
    if not folder or folder in RESERVED_STAGING_FOLDERS:
        return False
    if " " in folder or folder.startswith("_"):
        return False
    return "@" in folder


def normalize_labeler_email(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    _name, addr = parseaddr(value.strip())
    candidate = (addr or value).strip().lower()
    if looks_like_labeler_email(candidate):
        return candidate
    match = EMAIL_IN_TEXT_RE.search(value)
    if match and looks_like_labeler_email(match.group(0).lower()):
        return match.group(0).lower()
    return None


def parse_original_from_forward_body(body: str) -> Optional[str]:
    """Best-effort original sender from a forwarded email body."""
    if not body:
        return None
    # Prefer the first From: after a forwarded-message marker when present.
    lowered = body.lower()
    marker_idx = -1
    for marker in (
        "forwarded message",
        "begin forwarded message",
        "---------- forwarded",
        "original message",
    ):
        marker_idx = lowered.find(marker)
        if marker_idx >= 0:
            break
    search = body[marker_idx:] if marker_idx >= 0 else body
    for match in FORWARDED_FROM_RE.finditer(search):
        email = normalize_labeler_email(match.group(1))
        if email and email != "alai@halocollar.com":
            return email
        if email:
            # Keep scanning; envelope From may appear before original.
            continue
    return None


def forward_body_from_meta(meta: Optional[Dict[str, Any]]) -> Optional[str]:
    """Pull forwarded-message text Make stored on _meta (e.g. Email Body)."""
    if not meta:
        return None
    for key in ("Email Body", "email_body", "body", "Body"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def resolve_forward_labeler(
    meta: Optional[Dict[str, Any]],
    body: Optional[str] = None,
    override: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """
    Resolve true labeler for a quarantine batch.

    Returns (email, source) where source is
    override|meta|meta.attribution|meta.body|body|none.
    """
    if override:
        email = normalize_labeler_email(override)
        if email:
            return email, "override"

    meta = meta or {}
    for key in (
        "Original Labeler Email Address",
        "original_labeler_email",
        "original_from",
    ):
        email = normalize_labeler_email(meta.get(key))
        if email:
            return email, "meta"

    attribution = meta.get("attribution")
    if isinstance(attribution, dict):
        for key in ("original_sender", "original_from", "labeler_email"):
            email = normalize_labeler_email(attribution.get(key))
            if email:
                return email, "meta.attribution"

    # Prefer explicit body arg (email_body.txt); fall back to meta "Email Body".
    body_text = body if (body and body.strip()) else forward_body_from_meta(meta)
    email = parse_original_from_forward_body(body_text or "")
    if email:
        source = "body" if (body and body.strip()) else "meta.body"
        return email, source

    return None, "none"


@dataclass
class StagingFile:
    key: str
    email: str
    message_id: str
    filename: str
    timestamp: str
    index: int
    kind: str
    family: str = "activity"
    size: int = 0


# Warn when staging file refs are this many times larger than unique session files.
DUPLICATE_RATIO_WARN = 3.0
# Promote: batch looks cumulative if this fraction of its extracted names
# already exist under the destination labeler.
CUMULATIVE_OVERLAP_WARN = 0.85


def analyze_staging_health(files: List[StagingFile]) -> Dict[str, Any]:
    """
    Detect duplicate session copies, incomplete trios, and size mismatches.

    Process already dedupes by (email, family, timestamp, index); this surfaces
    Make/quarantine stacking so we notice before S3/process blows up.
    """
    by_session: Dict[Tuple[str, str, str, int], List[StagingFile]] = defaultdict(list)
    for f in files:
        by_session[(f.email, f.family, f.timestamp, f.index)].append(f)

    multi_message_sessions = 0
    size_mismatch_sessions = 0
    incomplete_sessions = 0
    duplicate_file_refs = 0
    mismatch_samples: List[Dict[str, Any]] = []
    incomplete_samples: List[Dict[str, Any]] = []

    for (email, family, timestamp, index), members in by_session.items():
        mids = {m.message_id for m in members}
        if len(mids) > 1:
            multi_message_sessions += 1
            # Count extra copies beyond one trio (or partial) worth of kinds.
            by_kind_mids: Dict[str, Set[str]] = defaultdict(set)
            by_kind_sizes: Dict[str, Set[int]] = defaultdict(set)
            for m in members:
                by_kind_mids[m.kind].add(m.message_id)
                by_kind_sizes[m.kind].add(int(m.size or 0))
            for mid_set in by_kind_mids.values():
                duplicate_file_refs += max(0, len(mid_set) - 1)
            if any(len(sizes) > 1 for sizes in by_kind_sizes.values()):
                size_mismatch_sessions += 1
                if len(mismatch_samples) < 8:
                    mismatch_samples.append(
                        {
                            "email": email,
                            "family": family,
                            "timestamp": timestamp,
                            "index": index,
                            "message_ids": sorted(mids)[:6],
                            "message_id_count": len(mids),
                        }
                    )

        expected = {"collar_collected", "durations", "user_reported"}
        # Completeness from latest message_id only (what process keeps).
        latest_mid = max(mids)
        latest_kinds = {m.kind for m in members if m.message_id == latest_mid}
        if not expected.issubset(latest_kinds):
            incomplete_sessions += 1
            if len(incomplete_samples) < 8:
                incomplete_samples.append(
                    {
                        "email": email,
                        "family": family,
                        "timestamp": timestamp,
                        "index": index,
                        "message_id": latest_mid,
                        "kinds": sorted(latest_kinds),
                        "missing": sorted(expected - latest_kinds),
                    }
                )

    unique_sessions = len(by_session)
    unique_file_estimate = 0
    for members in by_session.values():
        latest_mid = max(m.message_id for m in members)
        unique_file_estimate += len(
            {m.kind for m in members if m.message_id == latest_mid}
        )
    raw_files = len(files)
    ratio = (raw_files / unique_file_estimate) if unique_file_estimate else 0.0

    warnings: List[str] = []
    if ratio >= DUPLICATE_RATIO_WARN:
        warnings.append(
            f"Staging has {raw_files} extracted files but only ~{unique_file_estimate} "
            f"unique after session dedupe ({ratio:.1f}x). Make/quarantine is likely "
            f"re-uploading cumulative extracted trees."
        )
    if size_mismatch_sessions:
        warnings.append(
            f"{size_mismatch_sessions} session(s) have the same id in multiple emails "
            f"with differing file sizes — dedupe kept the latest message_id; inspect samples."
        )
    if incomplete_sessions:
        warnings.append(
            f"{incomplete_sessions} session(s) missing collar_collected/durations/user_reported "
            f"in the winning message batch."
        )

    return {
        "raw_extracted_files": raw_files,
        "unique_sessions": unique_sessions,
        "unique_files_after_dedupe": unique_file_estimate,
        "duplicate_file_refs": duplicate_file_refs,
        "multi_message_sessions": multi_message_sessions,
        "size_mismatch_sessions": size_mismatch_sessions,
        "incomplete_sessions": incomplete_sessions,
        "duplicate_ratio": round(ratio, 2),
        "warnings": warnings,
        "mismatch_samples": mismatch_samples,
        "incomplete_samples": incomplete_samples,
    }


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
    incomplete_sessions: int = 0
    health: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
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
            "incomplete_sessions": self.incomplete_sessions,
            "health": self.health,
            "warnings": self.warnings,
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
                if not looks_like_labeler_email(email):
                    continue
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
                        family=match.group("family"),
                        size=int(obj.get("Size") or 0),
                    )
                )
        return files

    @property
    def forwards_prefix(self) -> str:
        return f"{self.staging_prefix}{FORWARDS_FOLDER}/"

    @property
    def forwards_ledger_key(self) -> str:
        return f"{self.staging_prefix}{FORWARDS_LEDGER_KEY_SUFFIX}"

    def list_forward_batches(self) -> List[Dict[str, Any]]:
        """Inventory quarantine batches under staging/_forwards/<message_id>/."""
        by_id: Dict[str, Dict[str, Any]] = {}
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.forwards_prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if key.endswith("/") or key == self.forwards_ledger_key:
                    continue
                rel = key[len(self.forwards_prefix) :]
                parts = [p for p in rel.split("/") if p]
                if not parts:
                    continue
                message_id = parts[0]
                if message_id.startswith("_"):
                    continue
                batch = by_id.setdefault(
                    message_id,
                    {
                        "message_id": message_id,
                        "keys": 0,
                        "extracted_files": 0,
                        "has_meta": False,
                        "has_body": False,
                        "zip_keys": [],
                        "prefix": f"{self.forwards_prefix}{message_id}/",
                    },
                )
                batch["keys"] += 1
                name = parts[-1]
                if name == "_meta.json":
                    batch["has_meta"] = True
                elif name == "email_body.txt":
                    batch["has_body"] = True
                elif name.lower().endswith(".zip"):
                    batch["zip_keys"].append(key)
                elif len(parts) >= 2 and parts[1] == "extracted" and name.endswith(".txt"):
                    batch["extracted_files"] += 1
        return [by_id[k] for k in sorted(by_id)]

    def pending_forwards(self) -> Dict[str, Any]:
        """
        Quarantine batches that still need promotion into staging/<labeler>/.

        Used by the Labeling Data UI: small batches can auto-promote; larger ones
        should be user-triggered.
        """
        pending: List[Dict[str, Any]] = []
        already: List[Dict[str, Any]] = []
        unresolved: List[Dict[str, Any]] = []

        for batch in self.list_forward_batches():
            message_id = batch["message_id"]
            prefix = batch["prefix"]
            meta = (
                self._load_json_object(f"{prefix}_meta.json")
                if batch["has_meta"]
                else None
            )
            if meta and isinstance(meta.get("promoted_to"), dict):
                already.append(
                    {
                        "message_id": message_id,
                        "promoted_to": meta["promoted_to"],
                        "keys": batch["keys"],
                    }
                )
                continue

            body = None
            if batch["has_body"]:
                try:
                    body = self._get_text(f"{prefix}email_body.txt")
                except Exception:  # noqa: BLE001
                    body = None

            labeler, source = resolve_forward_labeler(meta, body=body)
            item = {
                "message_id": message_id,
                "keys": batch["keys"],
                "extracted_files": batch["extracted_files"],
                "has_meta": batch["has_meta"],
                "has_body_file": batch["has_body"],
                "has_meta_body": bool(forward_body_from_meta(meta)),
                "labeler_email": labeler,
                "labeler_resolved_from": source,
                "auto_promote": bool(
                    labeler and int(batch["keys"] or 0) <= AUTO_PROMOTE_MAX_KEYS
                ),
            }
            if labeler:
                pending.append(item)
            else:
                unresolved.append(item)

        total_keys = sum(int(p["keys"] or 0) for p in pending)
        return {
            "pending": pending,
            "already_promoted": already,
            "unresolved": unresolved,
            "pending_count": len(pending),
            "pending_keys": total_keys,
            "auto_promote": bool(
                pending
                and not unresolved
                and total_keys <= AUTO_PROMOTE_MAX_KEYS
                and all(p.get("auto_promote") for p in pending)
            ),
            "auto_promote_max_keys": AUTO_PROMOTE_MAX_KEYS,
        }

    def _load_json_object(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else None
        except Exception:  # noqa: BLE001
            return None

    def _put_json_object(self, key: str, data: Dict[str, Any], dry_run: bool) -> None:
        if dry_run:
            return
        body = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

    def _copy_key(self, src: str, dest: str, dry_run: bool) -> None:
        if dry_run or src == dest:
            return
        self.s3_client.copy_object(
            Bucket=self.bucket_name,
            CopySource={"Bucket": self.bucket_name, "Key": src},
            Key=dest,
        )

    def _labeler_extracted_filenames(self, labeler: str) -> Set[str]:
        """Filenames already under staging/<labeler>/*/extracted/."""
        names: Set[str] = set()
        prefix = f"{self.staging_prefix}{labeler}/"
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                parts = key.split("/")
                # staging/<email>/<mid>/extracted/<filename>
                if len(parts) >= 5 and parts[-2] == "extracted":
                    names.add(parts[-1])
        return names

    def _append_forward_attribution(
        self, entry: Dict[str, Any], dry_run: bool
    ) -> None:
        ledger = self._load_json_object(self.forwards_ledger_key) or {
            "schema_version": 1,
            "entries": [],
        }
        entries = ledger.get("entries")
        if not isinstance(entries, list):
            entries = []
        # Replace prior entry for same quarantine message_id.
        mid = entry.get("quarantine_message_id")
        entries = [e for e in entries if e.get("quarantine_message_id") != mid]
        entries.append(entry)
        ledger["entries"] = entries
        ledger["updated_at"] = entry.get("promoted_at")
        self._put_json_object(self.forwards_ledger_key, ledger, dry_run=dry_run)

    def promote_forwards(
        self,
        dry_run: bool = False,
        labeler_overrides: Optional[Dict[str, str]] = None,
        default_labeler: Optional[str] = None,
        message_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Rehome staging/_forwards/<id>/ → staging/<labeler>/<id>/ for process_staging.

        Attribution is recorded in:
          - promoted batch _meta.json (attribution block)
          - staging/_forwards/_attributions.json ledger
          - quarantine _meta.json updated with promoted_to (when meta exists)

        Labeler resolution order per batch:
          override / --labeler → meta original fields → email_body.txt →
          meta "Email Body" → default_labeler
        """
        overrides = {
            (k or "").strip(): (v or "").strip().lower()
            for k, v in (labeler_overrides or {}).items()
        }
        default = normalize_labeler_email(default_labeler)
        want = set(message_ids) if message_ids else None

        report: Dict[str, Any] = {
            "bucket": self.bucket_name,
            "forwards_prefix": self.forwards_prefix,
            "dry_run": dry_run,
            "promoted": [],
            "skipped": [],
            "errors": [],
            "warnings": [],
        }
        # Avoid re-promoting cumulative extracted trees Make stacked into each forward.
        labeler_extracted_cache: Dict[str, Set[str]] = {}

        batches = self.list_forward_batches()
        for batch in batches:
            message_id = batch["message_id"]
            if want is not None and message_id not in want:
                continue

            prefix = batch["prefix"]
            meta_key = f"{prefix}_meta.json"
            body_key = f"{prefix}email_body.txt"
            meta = self._load_json_object(meta_key) if batch["has_meta"] else None
            if meta and isinstance(meta.get("promoted_to"), dict):
                report["skipped"].append(
                    {
                        "message_id": message_id,
                        "reason": "already_promoted",
                        "promoted_to": meta.get("promoted_to"),
                    }
                )
                continue

            body = None
            if batch["has_body"]:
                try:
                    body = self._get_text(body_key)
                except Exception as exc:  # noqa: BLE001
                    report["errors"].append(
                        {"message_id": message_id, "error": f"read body: {exc}"}
                    )

            override = overrides.get(message_id) or default
            labeler, source = resolve_forward_labeler(meta, body=body, override=override)
            if not labeler:
                report["skipped"].append(
                    {
                        "message_id": message_id,
                        "reason": "unresolved_labeler",
                        "has_meta": batch["has_meta"],
                        "has_body": batch["has_body"],
                        "extracted_files": batch["extracted_files"],
                    }
                )
                continue

            dest_prefix = f"{self.staging_prefix}{labeler}/{message_id}/"
            if labeler not in labeler_extracted_cache:
                labeler_extracted_cache[labeler] = self._labeler_extracted_filenames(
                    labeler
                )
            existing_extracted = labeler_extracted_cache[labeler]

            keys_to_copy: List[Tuple[str, str]] = []
            skipped_duplicate_extracted = 0
            extracted_seen = 0
            new_extracted_names: Set[str] = set()
            paginator = self.s3_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                for obj in page.get("Contents", []) or []:
                    src = obj["Key"]
                    if src.endswith("/"):
                        continue
                    rel = src[len(prefix) :]
                    if not rel or rel in ("_meta.json",):
                        # Meta rewritten below with attribution.
                        continue
                    if rel.startswith("extracted/"):
                        extracted_seen += 1
                        fname = rel.split("/", 1)[-1]
                        if fname in existing_extracted:
                            skipped_duplicate_extracted += 1
                            continue
                        new_extracted_names.add(fname)
                        dest = f"{dest_prefix}{rel}"
                    elif rel.startswith("raw/"):
                        dest = f"{dest_prefix}{rel}"
                    elif rel.lower().endswith(".zip"):
                        # Quarantine sometimes drops zip at batch root.
                        dest = f"{dest_prefix}raw/{rel.split('/')[-1]}"
                    else:
                        dest = f"{dest_prefix}{rel}"
                    keys_to_copy.append((src, dest))

            overlap = (
                (skipped_duplicate_extracted / extracted_seen) if extracted_seen else 0.0
            )
            cumulative = overlap >= CUMULATIVE_OVERLAP_WARN and extracted_seen > 0
            if cumulative:
                warn = (
                    f"Forward {message_id} looks cumulative for {labeler}: "
                    f"{skipped_duplicate_extracted}/{extracted_seen} extracted files "
                    f"already in staging (overlap {overlap:.0%}). "
                    f"Copied only {len(new_extracted_names)} new extracted file(s)."
                )
                report["warnings"].append(warn)
                logger.warning(warn)

            envelope_from = None
            if meta:
                envelope_from = normalize_labeler_email(
                    meta.get("Labeler Email Address")
                    or meta.get("envelope_from")
                    or (meta.get("envelope") or {}).get("from_email")
                )

            promoted_at = datetime.now(timezone.utc).isoformat()
            attribution = {
                "source": "forward",
                "forwarded": True,
                "quarantine_prefix": prefix,
                "quarantine_message_id": message_id,
                "labeler_resolved_from": source,
                "original_sender": labeler,
                "forwarder": envelope_from or "alai@halocollar.com",
                "promoted_at": promoted_at,
                "skipped_duplicate_extracted": skipped_duplicate_extracted,
                "new_extracted_files": len(new_extracted_names),
                "likely_cumulative_extract": cumulative,
            }

            new_meta: Dict[str, Any] = deepcopy(meta) if meta else {}
            new_meta["Labeler Email Address"] = labeler
            new_meta["Original Labeler Email Address"] = labeler
            if envelope_from:
                new_meta["Forwarder Email Address"] = envelope_from
            new_meta["needs_attribution"] = False
            new_meta["attribution"] = attribution
            if "schema_version" not in new_meta:
                new_meta["schema_version"] = 1
            if "source" not in new_meta:
                new_meta["source"] = "gmail-make-forward-promoted"

            try:
                for src, dest in keys_to_copy:
                    self._copy_key(src, dest, dry_run=dry_run)
                existing_extracted.update(new_extracted_names)
                self._put_json_object(
                    f"{dest_prefix}_meta.json", new_meta, dry_run=dry_run
                )

                if meta is not None:
                    quarantine_meta = deepcopy(meta)
                    quarantine_meta["needs_attribution"] = False
                    quarantine_meta["promoted_to"] = {
                        "email": labeler,
                        "prefix": dest_prefix,
                        "promoted_at": promoted_at,
                        "skipped_duplicate_extracted": skipped_duplicate_extracted,
                        "new_extracted_files": len(new_extracted_names),
                    }
                    quarantine_meta["attribution"] = attribution
                    self._put_json_object(meta_key, quarantine_meta, dry_run=dry_run)

                ledger_entry = {
                    "quarantine_message_id": message_id,
                    "labeler_email": labeler,
                    "forwarder": attribution["forwarder"],
                    "labeler_resolved_from": source,
                    "quarantine_prefix": prefix,
                    "staging_prefix": dest_prefix,
                    "promoted_at": promoted_at,
                    "extracted_files": batch["extracted_files"],
                    "copied_keys": len(keys_to_copy) + 1,
                    "skipped_duplicate_extracted": skipped_duplicate_extracted,
                    "new_extracted_files": len(new_extracted_names),
                    "likely_cumulative_extract": cumulative,
                    "dry_run": dry_run,
                }
                self._append_forward_attribution(ledger_entry, dry_run=dry_run)

                report["promoted"].append(
                    {
                        "message_id": message_id,
                        "labeler_email": labeler,
                        "labeler_resolved_from": source,
                        "dest_prefix": dest_prefix,
                        "copied_keys": len(keys_to_copy) + 1,
                        "extracted_files": batch["extracted_files"],
                        "skipped_duplicate_extracted": skipped_duplicate_extracted,
                        "new_extracted_files": len(new_extracted_names),
                        "likely_cumulative_extract": cumulative,
                    }
                )
                logger.info(
                    "Promoted forward %s → %s (from=%s, keys=%s, new_extracted=%s, skipped_dup=%s)",
                    message_id,
                    labeler,
                    source,
                    len(keys_to_copy) + 1,
                    len(new_extracted_names),
                    skipped_duplicate_extracted,
                )
            except Exception as exc:  # noqa: BLE001
                report["errors"].append(
                    {"message_id": message_id, "error": str(exc)}
                )

        return report

    def staging_status(self) -> Dict[str, Any]:
        """Lightweight inventory of staging batches vs processed output."""
        staging_files = self.list_staging_extracted()
        batches = sorted({(f.email, f.message_id) for f in staging_files})
        by_email: Dict[str, int] = defaultdict(int)
        staging_by_family: Dict[str, int] = defaultdict(int)
        for f in staging_files:
            by_email[f.email] += 1
            staging_by_family[f.family] += 1

        forward_batches = self.list_forward_batches()
        attributions = self._load_json_object(self.forwards_ledger_key) or {}
        pending_forwards = self.pending_forwards()

        output_count = 0
        output_emails = set()
        output_by_family: Dict[str, int] = defaultdict(int)
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
                fname = parts[-1] if parts else ""
                if fname.startswith("gps_session_"):
                    output_by_family["gps"] += 1
                elif fname.startswith("activity_session_"):
                    output_by_family["activity"] += 1

        return {
            "bucket": self.bucket_name,
            "staging_prefix": self.staging_prefix,
            "output_prefix": self.output_prefix,
            "staging_batches": len(batches),
            "staging_extracted_files": len(staging_files),
            "staging_by_email": dict(sorted(by_email.items())),
            "staging_by_family": dict(sorted(staging_by_family.items())),
            "staging_batch_ids": [
                {"email": e, "message_id": m} for e, m in batches
            ],
            "forward_batches": len(forward_batches),
            "forward_batch_ids": [b["message_id"] for b in forward_batches],
            "forward_extracted_files": sum(
                int(b.get("extracted_files") or 0) for b in forward_batches
            ),
            "forward_attributions": len(attributions.get("entries") or []),
            "pending_forwards": pending_forwards,
            "staging_health": analyze_staging_health(staging_files),
            "output_files": output_count,
            "output_by_family": dict(sorted(output_by_family.items())),
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

    def _list_output_keys(self) -> Set[str]:
        keys: Set[str] = set()
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.output_prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if not key.endswith("/"):
                    keys.add(key)
        return keys

    def _resolve_collar_sn(self, collar_key: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Return (sn, error)."""
        if not collar_key:
            return None, None
        try:
            text = self._get_text(collar_key)
            match = COLLAR_SN_RE.search(text)
            if match:
                return sanitize_collar_sn(match.group(1)), None
            return None, None
        except Exception as exc:  # noqa: BLE001
            return None, f"read SN failed: {exc}"

    def process_staging(
        self,
        dry_run: bool = False,
        clear_output: bool = True,
        workers: int = 16,
    ) -> Dict[str, Any]:
        """
        Process all staging extracted files into extracted-txt/<email>/<collar-sn>/.

        Dedupes identical sessions across message_ids (keeps latest message_id).
        Skips dest keys that already exist (no per-file MD5) unless clear_output.

        Args:
            dry_run: Plan only; do not copy/delete.
            clear_output: Wipe extracted-txt/ before copying (clean reprocess).
            workers: Parallel S3 copy / SN-read threads.
        """
        report = ProcessReport(
            bucket=self.bucket_name,
            staging_prefix=self.staging_prefix,
            output_prefix=self.output_prefix,
            dry_run=dry_run,
        )
        workers = max(1, int(workers or 1))

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
        health = analyze_staging_health(files)
        report.health = health
        report.warnings = list(health.get("warnings") or [])
        report.incomplete_sessions = int(health.get("incomplete_sessions") or 0)
        for warning in report.warnings:
            logger.warning("Staging health: %s", warning)

        # Group by labeler + family + session identity (timestamp+index).
        # If the same session appears in multiple Gmail messages, prefer the
        # lexicographically latest message_id's files.
        sessions: Dict[Tuple[str, str, str, int], List[StagingFile]] = defaultdict(list)
        for f in files:
            sessions[(f.email, f.family, f.timestamp, f.index)].append(f)

        report.sessions = len(sessions)
        logger.info(
            "Staging inventory: %s files → %s unique sessions "
            "(~%s unique files after dedupe, %s duplicate refs)",
            len(files),
            len(sessions),
            health.get("unique_files_after_dedupe"),
            health.get("duplicate_file_refs"),
        )

        existing_dest: Set[str] = set()
        if not clear_output and not dry_run:
            existing_dest = self._list_output_keys()
            logger.info("Existing output keys: %s", len(existing_dest))

        # Resolve chosen files + collar keys first (CPU / local), then fetch SNs in parallel.
        planned: List[Dict[str, Any]] = []
        for (email, _family, _timestamp, _index), members in sorted(sessions.items()):
            by_kind: Dict[str, StagingFile] = {}
            for m in sorted(members, key=lambda x: x.message_id):
                by_kind[m.kind] = m
            chosen = list(by_kind.values())
            collar = by_kind.get("collar_collected")
            planned.append(
                {
                    "email": email,
                    "chosen": chosen,
                    "collar_key": collar.key if collar else None,
                    "message_ids": {m.message_id for m in chosen},
                }
            )

        sn_by_collar: Dict[str, Optional[str]] = {}
        collar_keys = [p["collar_key"] for p in planned if p["collar_key"]]
        if collar_keys:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(self._resolve_collar_sn, key): key for key in collar_keys
                }
                done = 0
                for fut in as_completed(futures):
                    key = futures[fut]
                    sn, err = fut.result()
                    sn_by_collar[key] = sn
                    if err:
                        report.errors.append({"key": key, "error": err})
                    done += 1
                    if done % 100 == 0 or done == len(futures):
                        logger.info("Resolved collar SN %s/%s", done, len(futures))

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
        copies: List[Tuple[str, str, str]] = []  # src, dest, email

        for item in planned:
            email = item["email"]
            collar_key = item["collar_key"]
            sn = sn_by_collar.get(collar_key) if collar_key else None
            if not sn:
                sn = UNKNOWN_COLLAR_SN
                report.unknown_sn_sessions += 1

            sn_seen.add(sn)
            by_email[email]["email"] = email
            by_email[email]["sessions"] += 1
            by_email[email]["collar_sns"].add(sn)
            by_email[email]["message_ids"].update(item["message_ids"])

            for m in item["chosen"]:
                dest = f"{self.output_prefix}{email}/{sn}/{m.filename}"
                if dry_run:
                    report.copied += 1
                    by_email[email]["files_copied"] += 1
                    continue
                if dest in existing_dest:
                    report.skipped_unchanged += 1
                    continue
                copies.append((m.key, dest, email))

        logger.info(
            "Copy plan: %s to copy, %s already present, dry_run=%s",
            len(copies),
            report.skipped_unchanged,
            dry_run,
        )

        if copies and not dry_run:
            def _copy_one(src_dest_email: Tuple[str, str, str]) -> Tuple[str, str, Optional[str]]:
                src, dest, email = src_dest_email
                try:
                    self.s3_client.copy_object(
                        Bucket=self.bucket_name,
                        CopySource={"Bucket": self.bucket_name, "Key": src},
                        Key=dest,
                    )
                    return email, dest, None
                except Exception as exc:  # noqa: BLE001
                    return email, dest, str(exc)

            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_copy_one, item) for item in copies]
                done = 0
                for fut in as_completed(futures):
                    email, dest, err = fut.result()
                    done += 1
                    if err:
                        report.errors.append({"dest": dest, "error": err})
                    else:
                        report.copied += 1
                        by_email[email]["files_copied"] += 1
                        existing_dest.add(dest)
                    if done % 100 == 0 or done == len(futures):
                        logger.info("Copied %s/%s", done, len(futures))

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
