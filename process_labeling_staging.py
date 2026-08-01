#!/usr/bin/env python3
"""
Process labeling staging uploads into extracted-txt/<email>/<collar-sn>/.

Usage:
  python process_labeling_staging.py --dry-run
  python process_labeling_staging.py
  python process_labeling_staging.py --no-clear-output
  python process_labeling_staging.py --status
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from backend.services.labeling_ingest_service import LabelingIngestService  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Plan only; no S3 writes")
    parser.add_argument(
        "--no-clear-output",
        action="store_true",
        help="Do not wipe extracted-txt/ before copying",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print staging vs output inventory and exit",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args(argv)

    svc = LabelingIngestService()

    if args.status:
        status = svc.staging_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"Bucket: s3://{status['bucket']}")
            print(
                f"Staging: {status['staging_extracted_files']} files in "
                f"{status['staging_batches']} batches under {status['staging_prefix']}"
            )
            for email, count in (status.get("staging_by_email") or {}).items():
                print(f"  {email}: {count} extracted files")
            fwd = status.get("forward_batches") or 0
            if fwd:
                print(
                    f"Forwards quarantine: {fwd} batches / "
                    f"{status.get('forward_extracted_files', 0)} extracted "
                    f"(not processed until promoted) "
                    f"ledger={status.get('forward_attributions', 0)}"
                )
            print(
                f"Output: {status['output_files']} files under {status['output_prefix']} "
                f"({', '.join(status['output_emails']) or 'none'})"
            )
        return 0

    report = svc.process_staging(
        dry_run=args.dry_run,
        clear_output=not args.no_clear_output,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Bucket: s3://{report['bucket']}")
        print(f"Staging prefix: {report['staging_prefix']}")
        print(f"Output prefix:  {report['output_prefix']}")
        print(f"dry_run={report['dry_run']}")
        print(
            f"Cleared output keys: {report['cleared_output_keys']} | "
            f"batches={report['staging_batches']} staging_files={report['staging_files']} "
            f"sessions={report['sessions']}"
        )
        print(
            f"Copied={report['copied']} skipped_unchanged={report['skipped_unchanged']} "
            f"unknown_sn_sessions={report['unknown_sn_sessions']} errors={len(report['errors'])}"
        )
        for email, stats in (report.get("by_email") or {}).items():
            print(
                f"  {email}: sessions={stats['sessions']} files={stats['files_copied']} "
                f"sns={','.join(stats['collar_sns']) or '-'} "
                f"msgs={len(stats['message_ids'])}"
            )
        if report["errors"]:
            print("Errors:", file=sys.stderr)
            for err in report["errors"][:20]:
                print(f"  {err}", file=sys.stderr)

    return 1 if report.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
