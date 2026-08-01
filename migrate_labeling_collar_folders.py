#!/usr/bin/env python3
"""
Migrate labeling exports to extracted-txt/<email>/<collar-sn>/<file>.

Keeps each session trio (collar_collected / durations / user_reported) together.
Collar SN is taken from:
  1) existing collar-sn folder (if already nested), else
  2) Collar SN line inside *_collar_collected.txt for that session, else
  3) _unknown

Usage:
  python migrate_labeling_collar_folders.py --dry-run
  python migrate_labeling_collar_folders.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from backend.services.labeling_data_analyzer import (  # noqa: E402
    FILENAME_RE,
    UNKNOWN_COLLAR_SN,
    LabelingDataAnalyzer,
    sanitize_collar_sn,
)
COLLAR_SN_RE = re.compile(r"Collar SN:\s*(.+)$", re.I | re.M)


def _session_key(email: str, timestamp: str, index: int) -> Tuple[str, str, int]:
    return email, timestamp, index


def plan_moves(analyzer: LabelingDataAnalyzer, dry_run: bool = True) -> Dict:
    client = analyzer.s3_client
    bucket = analyzer.bucket_name
    prefix = analyzer.prefix

    objects: List[Dict] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []) or []:
            key = obj["Key"]
            if key.endswith("/"):
                continue
            rel = key[len(prefix) :] if key.startswith(prefix) else key
            parts = [p for p in rel.split("/") if p]
            filename = parts[-1]
            match = FILENAME_RE.match(filename)
            if not match:
                continue
            if len(parts) == 2:
                email, _fname = parts
                collar_path = None
                layout = "legacy"
            elif len(parts) == 3:
                email, collar_path, _fname = parts
                layout = "nested"
            else:
                continue
            objects.append(
                {
                    "key": key,
                    "email": email,
                    "collar_path": collar_path,
                    "filename": filename,
                    "timestamp": match.group("timestamp"),
                    "index": int(match.group("index")),
                    "kind": match.group("kind"),
                    "layout": layout,
                }
            )

    sessions = defaultdict(list)
    for obj in objects:
        sessions[_session_key(obj["email"], obj["timestamp"], obj["index"])].append(obj)

    moves = []
    already_ok = 0
    for (email, timestamp, index), members in sorted(sessions.items()):
        sn: Optional[str] = None

        # Prefer SN from any already-nested path in the session
        for m in members:
            if m["collar_path"]:
                sn = sanitize_collar_sn(m["collar_path"])
                break

        # Else read from collar_collected body
        if not sn:
            for m in members:
                if m["kind"] != "collar_collected":
                    continue
                body = client.get_object(Bucket=bucket, Key=m["key"])["Body"].read()
                text = body.decode("utf-8", errors="replace")
                match = COLLAR_SN_RE.search(text)
                if match:
                    sn = sanitize_collar_sn(match.group(1))
                    break

        sn = sn or UNKNOWN_COLLAR_SN

        session_moves = []
        for m in members:
            dst = f"{prefix}{email}/{sn}/{m['filename']}"
            if m["key"] != dst:
                session_moves.append({"src": m["key"], "dst": dst, "collar_sn": sn})
        if not session_moves and all(m["layout"] == "nested" for m in members):
            already_ok += 1
        moves.extend(session_moves)

    executed = []
    errors = []
    if not dry_run:
        for move in moves:
            try:
                client.copy_object(
                    Bucket=bucket,
                    CopySource={"Bucket": bucket, "Key": move["src"]},
                    Key=move["dst"],
                )
                client.delete_object(Bucket=bucket, Key=move["src"])
                executed.append(move)
            except Exception as exc:  # noqa: BLE001
                errors.append({**move, "error": str(exc)})

    return {
        "bucket": bucket,
        "prefix": prefix,
        "sessions": len(sessions),
        "already_nested_sessions": already_ok,
        "moves_planned": len(moves),
        "moves": moves,
        "executed": len(executed),
        "errors": errors,
        "dry_run": dry_run,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; do not copy/delete")
    parser.add_argument("--bucket", default=None)
    parser.add_argument("--prefix", default=None)
    args = parser.parse_args(argv)

    analyzer = LabelingDataAnalyzer(bucket_name=args.bucket, prefix=args.prefix)
    # Default to dry-run unless explicitly omitted... safer: require --apply
    # User-friendly: --dry-run plans; without it applies.
    result = plan_moves(analyzer, dry_run=args.dry_run)

    print(f"Bucket: s3://{result['bucket']}/{result['prefix']}")
    print(
        f"Sessions: {result['sessions']} | already nested: {result['already_nested_sessions']} | "
        f"moves: {result['moves_planned']} | dry_run={result['dry_run']}"
    )
    for move in result["moves"][:30]:
        print(f"  {move['src']}\n    -> {move['dst']}")
    if result["moves_planned"] > 30:
        print(f"  ... +{result['moves_planned'] - 30} more")
    if result["errors"]:
        print(f"Errors: {len(result['errors'])}", file=sys.stderr)
        for err in result["errors"][:10]:
            print(f"  {err}", file=sys.stderr)
        return 1
    if args.dry_run:
        print("\nDry run only. Re-run without --dry-run to apply.")
    else:
        print(f"\nApplied {result['executed']} moves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
