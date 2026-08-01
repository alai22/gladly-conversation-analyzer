"""
Halo AI labeling data analyzer.

Reads activity-session .txt files from S3 and reports:
- file / session counts grouped by user (and collar SN)
- labeled activity volume from durations, collar_collected, and user_reported files

Expected layout (preferred):
  extracted-txt/<labeler-email>/<collar-sn>/activity_session_*.txt

Legacy layout (still supported):
  extracted-txt/<labeler-email>/activity_session_*.txt

Related session files (collar_collected / durations / user_reported) share a timestamp+index
and should live in the same collar-sn folder even when only collar_collected contains the SN.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import boto3

from ..utils.config import Config
from ..utils.logging import get_logger

logger = get_logger("labeling_data_analyzer")

FILE_KINDS = ("collar_collected", "durations", "user_reported")
UNKNOWN_COLLAR_SN = "_unknown"

FILENAME_RE = re.compile(
    r"^activity_session_(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_"
    r"(?P<index>\d+)_(?P<kind>collar_collected|durations|user_reported)\.txt$"
)

# "Standing (10)" or "OnShelf (12) (initial state)"
ACTIVITY_RE = re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9]*)\s*\((?P<id>\d+)\)")

# "18:38:31.150 / 18:38:29.000: OnShelf (12) (initial state)"
# "18:38:47.095: End of session"
# "18:38:31.123: Dog's name: Diamond"
COLLAR_LINE_RE = re.compile(
    r"^(?P<ts>\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
    r"(?:\s*/\s*(?P<device_ts>\d{2}:\d{2}:\d{2}(?:\.\d+)?))?"
    r":\s*(?P<body>.+)$"
)

# "18:38:43.112: Standing (10) (touch start)"
USER_REPORTED_RE = re.compile(
    r"^(?P<ts>\d{2}:\d{2}:\d{2}(?:\.\d+)?):\s*"
    r"(?P<activity>[A-Za-z][A-Za-z0-9]*)\s*\((?P<id>\d+)\)"
    r"(?:\s*\((?P<event>[^)]+)\))?$"
)

DURATION_RE = re.compile(
    r"^(?P<h>\d+):(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<frac>\d+))?$"
)


def parse_duration_to_seconds(value: str) -> float:
    """Convert HH:MM:SS[.fraction] duration strings to seconds."""
    if not value or not isinstance(value, str):
        return 0.0
    match = DURATION_RE.match(value.strip())
    if not match:
        return 0.0
    hours = int(match.group("h"))
    minutes = int(match.group("m"))
    seconds = int(match.group("s"))
    frac = match.group("frac") or "0"
    # Normalize fractional part to microseconds-scale float
    frac_seconds = float(f"0.{frac}")
    return hours * 3600 + minutes * 60 + seconds + frac_seconds


def format_seconds(total_seconds: float) -> str:
    """Human-readable duration from seconds."""
    if total_seconds < 0:
        total_seconds = 0.0
    td = timedelta(seconds=total_seconds)
    # timedelta string is like "0:00:01.500000" or "1 day, 0:00:01"
    return str(td)


def parse_activity_label(label: str) -> Optional[Tuple[str, int]]:
    """Parse 'Standing (10)' -> ('Standing', 10)."""
    match = ACTIVITY_RE.search(label or "")
    if not match:
        return None
    return match.group("name"), int(match.group("id"))


def sanitize_collar_sn(sn: Optional[str]) -> str:
    """Normalize collar SN for use as an S3 path segment."""
    if not sn or not str(sn).strip():
        return UNKNOWN_COLLAR_SN
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(sn).strip()).strip("._-")
    return cleaned or UNKNOWN_COLLAR_SN


def parse_rel_path(rel: str) -> Optional[Dict[str, Any]]:
    """
    Parse extracted-txt-relative path into user / optional collar_sn / filename.

    Supports:
      <email>/<file>
      <email>/<collar_sn>/<file>
    """
    parts = [p for p in (rel or "").split("/") if p]
    if len(parts) == 2:
        user, filename = parts
        parsed = parse_filename(filename)
        if not parsed:
            return None
        return {
            "user": user,
            "collar_sn": None,
            "filename": filename,
            **parsed,
        }
    if len(parts) == 3:
        user, collar_sn, filename = parts
        parsed = parse_filename(filename)
        if not parsed:
            return None
        return {
            "user": user,
            "collar_sn": sanitize_collar_sn(collar_sn),
            "filename": filename,
            **parsed,
        }
    return None


@dataclass
class SessionFileRef:
    key: str
    user: str
    filename: str
    timestamp: str
    index: int
    kind: str
    size: int = 0
    collar_sn: Optional[str] = None


@dataclass
class CollarCollectedParse:
    dog_name: Optional[str] = None
    dog_breed: Optional[str] = None
    dog_weight: Optional[float] = None
    collar_sn: Optional[str] = None
    activity_events: List[Dict[str, Any]] = field(default_factory=list)
    session_started: bool = False
    session_ended: bool = False


@dataclass
class UserReportedParse:
    events: List[Dict[str, Any]] = field(default_factory=list)


def parse_filename(filename: str) -> Optional[Dict[str, Any]]:
    match = FILENAME_RE.match(filename)
    if not match:
        return None
    return {
        "timestamp": match.group("timestamp"),
        "index": int(match.group("index")),
        "kind": match.group("kind"),
    }


def parse_collar_collected(text: str) -> CollarCollectedParse:
    result = CollarCollectedParse()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = COLLAR_LINE_RE.match(line)
        if not match:
            continue
        body = match.group("body").strip()
        body_lower = body.lower()

        if body_lower.startswith("dog's name:"):
            result.dog_name = body.split(":", 1)[1].strip()
            continue
        if body_lower.startswith("dog's breed:"):
            result.dog_breed = body.split(":", 1)[1].strip()
            continue
        if body_lower.startswith("dog's weight:"):
            try:
                result.dog_weight = float(body.split(":", 1)[1].strip())
            except ValueError:
                pass
            continue
        if body_lower.startswith("collar sn:"):
            result.collar_sn = body.split(":", 1)[1].strip()
            continue
        if body_lower == "session started":
            result.session_started = True
            continue
        if body_lower == "end of session":
            result.session_ended = True
            continue

        activity = parse_activity_label(body)
        if activity:
            name, activity_id = activity
            note = None
            # Capture trailing note like "(initial state)"
            note_match = re.search(r"\)\s*(\(.+\))\s*$", body)
            if note_match:
                note = note_match.group(1).strip("() ")
            result.activity_events.append(
                {
                    "timestamp": match.group("ts"),
                    "device_timestamp": match.group("device_ts"),
                    "activity": name,
                    "activity_id": activity_id,
                    "note": note,
                    "label": f"{name} ({activity_id})",
                }
            )
    return result


def parse_durations(text: str) -> Dict[str, float]:
    """Return map of activity label -> seconds."""
    data = json.loads(text)
    if not isinstance(data, dict):
        return {}
    out: Dict[str, float] = {}
    for label, duration in data.items():
        seconds = parse_duration_to_seconds(str(duration))
        out[str(label)] = seconds
    return out


def parse_user_reported(text: str) -> UserReportedParse:
    result = UserReportedParse()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = USER_REPORTED_RE.match(line)
        if not match:
            continue
        name = match.group("activity")
        activity_id = int(match.group("id"))
        result.events.append(
            {
                "timestamp": match.group("ts"),
                "activity": name,
                "activity_id": activity_id,
                "event": (match.group("event") or "").strip() or None,
                "label": f"{name} ({activity_id})",
            }
        )
    return result


class LabelingDataAnalyzer:
    """Analyze Halo AI labeling exports stored in S3."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        prefix: Optional[str] = None,
        region: Optional[str] = None,
        s3_client=None,
    ):
        self.bucket_name = bucket_name or Config.LABELING_S3_BUCKET_NAME
        self.prefix = (prefix or Config.LABELING_S3_PREFIX or "extracted-txt/").rstrip("/") + "/"
        self.region = region or Config.S3_REGION or "us-east-1"
        self.s3_client = s3_client or boto3.client("s3", region_name=self.region)

        if not self.bucket_name:
            raise ValueError("LABELING_S3_BUCKET_NAME is not configured")

    def list_session_files(self) -> List[SessionFileRef]:
        """List all recognized activity_session files under the prefix."""
        files: List[SessionFileRef] = []
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=self.prefix):
            for obj in page.get("Contents", []) or []:
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                rel = key[len(self.prefix) :] if key.startswith(self.prefix) else key
                parsed = parse_rel_path(rel)
                if not parsed:
                    continue
                files.append(
                    SessionFileRef(
                        key=key,
                        user=parsed["user"],
                        filename=parsed["filename"],
                        timestamp=parsed["timestamp"],
                        index=parsed["index"],
                        kind=parsed["kind"],
                        size=int(obj.get("Size") or 0),
                        collar_sn=parsed.get("collar_sn"),
                    )
                )
        return files

    def _get_text(self, key: str) -> str:
        body = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)["Body"].read()
        return body.decode("utf-8", errors="replace")

    def analyze(self, include_content: bool = True) -> Dict[str, Any]:
        """
        Inventory files by user and optionally parse contents for activity stats.

        Args:
            include_content: When True, download and parse durations / event files.
        """
        files = self.list_session_files()

        by_user: Dict[str, Dict[str, Any]] = {}
        activity_duration_seconds: Dict[str, float] = defaultdict(float)
        activity_collar_events: Dict[str, int] = defaultdict(int)
        activity_user_reported_events: Dict[str, int] = defaultdict(int)
        sessions_seen: Dict[str, set] = defaultdict(set)
        dogs: Dict[str, Dict[str, Any]] = {}
        parse_errors: List[Dict[str, str]] = []

        # Resolve collar SN per session: path folder first, then collar_collected body
        # so durations/user_reported stay grouped with their session even without SN in-file.
        session_collar: Dict[Tuple[str, str], str] = {}
        for ref in files:
            session_id = f"{ref.timestamp}_{ref.index}"
            if ref.collar_sn:
                session_collar[(ref.user, session_id)] = ref.collar_sn

        if include_content:
            for ref in files:
                if ref.kind != "collar_collected":
                    continue
                session_id = f"{ref.timestamp}_{ref.index}"
                sess_key = (ref.user, session_id)
                if sess_key in session_collar:
                    continue
                try:
                    text = self._get_text(ref.key)
                    parsed = parse_collar_collected(text)
                    if parsed.collar_sn:
                        session_collar[sess_key] = sanitize_collar_sn(parsed.collar_sn)
                except Exception as exc:  # noqa: BLE001
                    parse_errors.append({"key": ref.key, "error": str(exc)})

        for ref in files:
            user_stats = by_user.setdefault(
                ref.user,
                {
                    "user": ref.user,
                    "total_files": 0,
                    "bytes": 0,
                    "by_kind": {k: 0 for k in FILE_KINDS},
                    "sessions": 0,
                    "collar_sns": set(),
                    "by_collar": defaultdict(
                        lambda: {
                            "collar_sn": None,
                            "files": 0,
                            "sessions": set(),
                            "activity_duration_seconds": defaultdict(float),
                        }
                    ),
                    "activity_duration_seconds": defaultdict(float),
                    "collar_activity_events": defaultdict(int),
                    "user_reported_events": defaultdict(int),
                },
            )
            user_stats["total_files"] += 1
            user_stats["bytes"] += ref.size
            if ref.kind in user_stats["by_kind"]:
                user_stats["by_kind"][ref.kind] += 1

            session_id = f"{ref.timestamp}_{ref.index}"
            sessions_seen[ref.user].add(session_id)
            collar_sn = session_collar.get((ref.user, session_id)) or UNKNOWN_COLLAR_SN
            user_stats["collar_sns"].add(collar_sn)
            collar_stats = user_stats["by_collar"][collar_sn]
            collar_stats["collar_sn"] = collar_sn
            collar_stats["files"] += 1
            collar_stats["sessions"].add(session_id)

            if not include_content:
                continue

            try:
                text = self._get_text(ref.key)
            except Exception as exc:  # noqa: BLE001 - collect and continue
                parse_errors.append({"key": ref.key, "error": str(exc)})
                continue

            try:
                if ref.kind == "durations":
                    durations = parse_durations(text)
                    for label, seconds in durations.items():
                        activity_duration_seconds[label] += seconds
                        user_stats["activity_duration_seconds"][label] += seconds
                        collar_stats["activity_duration_seconds"][label] += seconds
                elif ref.kind == "collar_collected":
                    parsed = parse_collar_collected(text)
                    if parsed.dog_name or parsed.collar_sn:
                        dog_key = parsed.collar_sn or parsed.dog_name or "unknown"
                        dogs[dog_key] = {
                            "name": parsed.dog_name,
                            "breed": parsed.dog_breed,
                            "weight": parsed.dog_weight,
                            "collar_sn": parsed.collar_sn,
                            "users": sorted(
                                set(dogs.get(dog_key, {}).get("users", []) + [ref.user])
                            ),
                        }
                    for event in parsed.activity_events:
                        label = event["label"]
                        activity_collar_events[label] += 1
                        user_stats["collar_activity_events"][label] += 1
                elif ref.kind == "user_reported":
                    parsed = parse_user_reported(text)
                    for event in parsed.events:
                        label = event["label"]
                        activity_user_reported_events[label] += 1
                        user_stats["user_reported_events"][label] += 1
            except Exception as exc:  # noqa: BLE001
                parse_errors.append({"key": ref.key, "error": str(exc)})

        for user, stats in by_user.items():
            stats["sessions"] = len(sessions_seen.get(user, set()))
            stats["activity_duration_seconds"] = dict(stats["activity_duration_seconds"])
            stats["collar_activity_events"] = dict(stats["collar_activity_events"])
            stats["user_reported_events"] = dict(stats["user_reported_events"])
            stats["activity_duration_human"] = {
                k: format_seconds(v) for k, v in stats["activity_duration_seconds"].items()
            }
            stats["collar_sns"] = sorted(stats["collar_sns"])
            collars_out = []
            for sn, cstats in stats["by_collar"].items():
                dur = dict(cstats["activity_duration_seconds"])
                collars_out.append(
                    {
                        "collar_sn": sn,
                        "files": cstats["files"],
                        "sessions": len(cstats["sessions"]),
                        "activity_duration_seconds": dur,
                        "activity_duration_human": {
                            k: format_seconds(v) for k, v in dur.items()
                        },
                    }
                )
            stats["by_collar"] = sorted(
                collars_out, key=lambda c: (-c["sessions"], c["collar_sn"])
            )

        summary = {
            "bucket": self.bucket_name,
            "prefix": self.prefix,
            "total_files": len(files),
            "total_users": len(by_user),
            "total_sessions": sum(len(s) for s in sessions_seen.values()),
            "files_by_kind": {
                kind: sum(1 for f in files if f.kind == kind) for kind in FILE_KINDS
            },
            "users": sorted(by_user.values(), key=lambda u: (-u["total_files"], u["user"])),
            "activity_duration_seconds": dict(
                sorted(activity_duration_seconds.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "activity_duration_human": {
                k: format_seconds(v)
                for k, v in sorted(
                    activity_duration_seconds.items(), key=lambda kv: (-kv[1], kv[0])
                )
            },
            "collar_activity_events": dict(
                sorted(activity_collar_events.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "user_reported_events": dict(
                sorted(activity_user_reported_events.items(), key=lambda kv: (-kv[1], kv[0]))
            ),
            "dogs": list(dogs.values()),
            "parse_errors": parse_errors,
        }
        return summary

    def analyze_local(self, root_dir: str) -> Dict[str, Any]:
        """
        Analyze a local mirror of extracted-txt for offline/testing use.

        Accepts both <email>/<file> and <email>/<collar_sn>/<file>.
        """
        root = os.path.abspath(root_dir)
        files: List[SessionFileRef] = []
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                parsed = parse_rel_path(rel)
                if not parsed:
                    continue
                files.append(
                    SessionFileRef(
                        key=full,
                        user=parsed["user"],
                        filename=parsed["filename"],
                        timestamp=parsed["timestamp"],
                        index=parsed["index"],
                        kind=parsed["kind"],
                        size=os.path.getsize(full),
                        collar_sn=parsed.get("collar_sn"),
                    )
                )

        # Reuse analyze logic via a tiny shim
        class _Local:
            def get_paginator(self, _name):
                raise RuntimeError("unused")

            def get_object(self, Bucket, Key):  # noqa: N803
                with open(Key, "rb") as fh:
                    return {"Body": _BytesBody(fh.read())}

        class _BytesBody:
            def __init__(self, data: bytes):
                self._data = data

            def read(self):
                return self._data

        analyzer = LabelingDataAnalyzer(
            bucket_name="local",
            prefix="",
            region=self.region,
            s3_client=_Local(),
        )
        # Monkey-patch list to use local files
        analyzer.list_session_files = lambda: files  # type: ignore[method-assign]
        analyzer._get_text = lambda key: open(key, "r", encoding="utf-8", errors="replace").read()  # type: ignore[method-assign]
        return analyzer.analyze(include_content=True)


def _activity_rows(duration_map: Dict[str, float], include_zero: bool = False) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for label, seconds in sorted(duration_map.items(), key=lambda kv: (-kv[1], kv[0])):
        if not include_zero and seconds <= 0:
            continue
        parsed = parse_activity_label(label)
        rows.append(
            {
                "label": label,
                "name": parsed[0] if parsed else label,
                "activity_id": parsed[1] if parsed else None,
                "seconds": round(float(seconds), 3),
                "human": format_seconds(float(seconds)),
            }
        )
    return rows


def format_ui_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Shape analyze() output for the frontend dashboard."""
    duration_map = summary.get("activity_duration_seconds") or {}
    total_duration = float(sum(duration_map.values()))
    activity_rows = _activity_rows(duration_map, include_zero=False)
    all_activity_rows = _activity_rows(duration_map, include_zero=True)

    users_out: List[Dict[str, Any]] = []
    for user in summary.get("users") or []:
        user_durations = user.get("activity_duration_seconds") or {}
        user_total = float(sum(user_durations.values()))
        collars = []
        for collar in user.get("by_collar") or []:
            collar_durations = collar.get("activity_duration_seconds") or {}
            collar_total = float(sum(collar_durations.values()))
            collars.append(
                {
                    "collar_sn": collar.get("collar_sn"),
                    "sessions": collar.get("sessions", 0),
                    "files": collar.get("files", 0),
                    "total_duration_seconds": round(collar_total, 3),
                    "total_duration_human": format_seconds(collar_total),
                    "activities": _activity_rows(collar_durations, include_zero=False),
                }
            )
        users_out.append(
            {
                "email": user.get("user"),
                "sessions": user.get("sessions", 0),
                "files": user.get("total_files", 0),
                "bytes": user.get("bytes", 0),
                "by_kind": user.get("by_kind") or {},
                "collar_sns": user.get("collar_sns") or [],
                "collars": collars,
                "total_duration_seconds": round(user_total, 3),
                "total_duration_human": format_seconds(user_total),
                "activities": _activity_rows(user_durations, include_zero=False),
                "all_activities": _activity_rows(user_durations, include_zero=True),
                "collar_activity_events": user.get("collar_activity_events") or {},
                "user_reported_events": user.get("user_reported_events") or {},
            }
        )

    return {
        "bucket": summary.get("bucket"),
        "prefix": summary.get("prefix"),
        "totals": {
            "users": summary.get("total_users", 0),
            "sessions": summary.get("total_sessions", 0),
            "files": summary.get("total_files", 0),
            "files_by_kind": summary.get("files_by_kind") or {},
            "duration_seconds": round(total_duration, 3),
            "duration_human": format_seconds(total_duration),
        },
        "activities": activity_rows,
        "all_activities": all_activity_rows,
        "users": users_out,
        "collar_activity_events": summary.get("collar_activity_events") or {},
        "user_reported_events": summary.get("user_reported_events") or {},
        "dogs": summary.get("dogs") or [],
        "parse_errors": summary.get("parse_errors") or [],
    }


def print_report(summary: Dict[str, Any]) -> None:
    """Pretty-print an analyze() summary to stdout."""
    print(f"Bucket: s3://{summary['bucket']}/{summary['prefix']}")
    print(
        f"Users: {summary['total_users']}  |  Sessions: {summary['total_sessions']}  |  "
        f"Files: {summary['total_files']}"
    )
    print(
        "By kind: "
        + ", ".join(f"{k}={v}" for k, v in summary["files_by_kind"].items())
    )
    print()
    print("Files by user")
    print("-" * 72)
    for user in summary["users"]:
        kinds = user["by_kind"]
        print(
            f"{user['user']}: files={user['total_files']} sessions={user['sessions']} "
            f"collar={kinds.get('collar_collected', 0)} "
            f"durations={kinds.get('durations', 0)} "
            f"user_reported={kinds.get('user_reported', 0)} "
            f"bytes={user['bytes']}"
        )

    print()
    print("Activity duration totals (from *_durations.txt)")
    print("-" * 72)
    durations = summary.get("activity_duration_seconds") or {}
    nonzero = {k: v for k, v in durations.items() if v > 0}
    if not nonzero:
        print("(no non-zero durations)")
    else:
        for label, seconds in nonzero.items():
            print(f"  {label}: {format_seconds(seconds)} ({seconds:.3f}s)")
    zero_count = sum(1 for v in durations.values() if v == 0)
    if zero_count:
        print(f"  ({zero_count} activities with 0 total duration omitted)")

    print()
    print("Collar-collected activity events (transition counts)")
    print("-" * 72)
    for label, count in (summary.get("collar_activity_events") or {}).items():
        print(f"  {label}: {count}")

    print()
    print("User-reported activity events")
    print("-" * 72)
    for label, count in (summary.get("user_reported_events") or {}).items():
        print(f"  {label}: {count}")

    dogs = summary.get("dogs") or []
    if dogs:
        print()
        print("Dogs seen")
        print("-" * 72)
        for dog in dogs:
            print(
                f"  {dog.get('name')} | breed={dog.get('breed')} "
                f"weight={dog.get('weight')} sn={dog.get('collar_sn')} "
                f"users={', '.join(dog.get('users') or [])}"
            )

    errors = summary.get("parse_errors") or []
    if errors:
        print()
        print(f"Parse errors: {len(errors)}")
        for err in errors[:10]:
            print(f"  {err['key']}: {err['error']}")
