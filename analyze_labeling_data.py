#!/usr/bin/env python3
"""
Analyze Halo AI labeling data in S3.

Counts files/sessions by user email and aggregates activity volume from
*_durations.txt, *_collar_collected.txt, and *_user_reported.txt.

Usage:
  python analyze_labeling_data.py
  python analyze_labeling_data.py --json
  python analyze_labeling_data.py --inventory-only
  python analyze_labeling_data.py --local-dir tests/fixtures/labeling_tree
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()

from backend.services.labeling_data_analyzer import (  # noqa: E402
    LabelingDataAnalyzer,
    print_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze Halo AI labeling S3 exports")
    parser.add_argument(
        "--bucket",
        default=None,
        help="Override LABELING_S3_BUCKET_NAME",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Override LABELING_S3_PREFIX (default: extracted-txt/)",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="List/count files only; do not download and parse contents",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print full summary as JSON",
    )
    parser.add_argument(
        "--local-dir",
        default=None,
        help="Analyze a local mirror instead of S3 (for offline/testing)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write JSON summary to this path",
    )
    args = parser.parse_args(argv)

    analyzer = LabelingDataAnalyzer(bucket_name=args.bucket, prefix=args.prefix)

    if args.local_dir:
        summary = analyzer.analyze_local(args.local_dir)
    else:
        summary = analyzer.analyze(include_content=not args.inventory_only)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"Wrote {args.output}", file=sys.stderr)

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_report(summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
