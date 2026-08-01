#!/usr/bin/env python3
"""
Promote quarantine staging/_forwards/<message-id>/ into normal staging/<labeler>/<id>/.

Keeps the quarantine copy for audit. Records attribution in:
  - staging/<labeler>/<id>/_meta.json  (attribution.forwarded=true)
  - staging/_forwards/_attributions.json

Usage:
  python promote_labeling_forwards.py --status
  python promote_labeling_forwards.py --dry-run --labeler lindseyw7485@gmail.com
  python promote_labeling_forwards.py --labeler lindseyw7485@gmail.com \\
      --message-id 19fbbf69aca7bc15
  python promote_labeling_forwards.py --map 19fbbf69aca7bc15=lindseyw7485@gmail.com
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from backend.services.labeling_ingest_service import LabelingIngestService  # noqa: E402


def _parse_map(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise argparse.ArgumentTypeError(
                f"--map expects message_id=email, got {raw!r}"
            )
        mid, email = raw.split("=", 1)
        mid, email = mid.strip(), email.strip().lower()
        if not mid or not email:
            raise argparse.ArgumentTypeError(f"invalid --map {raw!r}")
        out[mid] = email
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no S3 writes")
    parser.add_argument(
        "--status",
        action="store_true",
        help="List quarantine batches and exit",
    )
    parser.add_argument(
        "--labeler",
        help="Default labeler email when body/meta cannot resolve original From",
    )
    parser.add_argument(
        "--message-id",
        action="append",
        dest="message_ids",
        default=None,
        help="Only promote this Gmail message id (repeatable)",
    )
    parser.add_argument(
        "--map",
        action="append",
        dest="maps",
        default=[],
        metavar="MESSAGE_ID=EMAIL",
        help="Per-batch labeler override (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args(argv)

    svc = LabelingIngestService()

    if args.status:
        batches = svc.list_forward_batches()
        status = {
            "bucket": svc.bucket_name,
            "forwards_prefix": svc.forwards_prefix,
            "batches": batches,
            "ledger_key": svc.forwards_ledger_key,
            "attributions": (svc._load_json_object(svc.forwards_ledger_key) or {}).get(
                "entries", []
            ),
        }
        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            print(f"Bucket: s3://{status['bucket']}")
            print(f"Quarantine: {status['forwards_prefix']} ({len(batches)} batches)")
            for b in batches:
                print(
                    f"  {b['message_id']}: keys={b['keys']} extracted={b['extracted_files']} "
                    f"meta={b['has_meta']} body={b['has_body']} zips={len(b['zip_keys'])}"
                )
            attrs = status["attributions"]
            print(f"Ledger: {len(attrs)} attribution entries → {status['ledger_key']}")
        return 0

    overrides = _parse_map(args.maps)
    report = svc.promote_forwards(
        dry_run=args.dry_run,
        labeler_overrides=overrides,
        default_labeler=args.labeler,
        message_ids=args.message_ids,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Bucket: s3://{report['bucket']}")
        print(f"dry_run={report['dry_run']}")
        print(
            f"promoted={len(report['promoted'])} skipped={len(report['skipped'])} "
            f"errors={len(report['errors'])}"
        )
        for item in report["promoted"]:
            print(
                f"  ✓ {item['message_id']} → {item['labeler_email']} "
                f"(via {item['labeler_resolved_from']}, keys={item['copied_keys']})"
            )
        for item in report["skipped"]:
            print(
                f"  · skipped {item['message_id']}: {item['reason']} "
                f"(meta={item.get('has_meta')} body={item.get('has_body')})"
            )
        for err in report["errors"][:20]:
            print(f"  ! {err}", file=sys.stderr)

    if report["errors"]:
        return 1
    if not report["promoted"] and report["skipped"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
