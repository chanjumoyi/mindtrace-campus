#!/usr/bin/env python3
"""Build an attempt-level emotion manifest from private collector JSON files.

The output contains paths, participant identifiers and labels.  Keep it in a
git-ignored private directory; never commit it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mindtrace_emotion.sessions import (
    build_manifest_rows,
    json_files,
    load_labels,
    manifest_summary,
    write_manifest,
)
from mindtrace_emotion.splits import assign_participant_splits

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="directory or one session JSON")
    parser.add_argument("--labels", type=Path, help="private label CSV")
    parser.add_argument("--output", type=Path, default=ROOT / "ml/emotion/data/manifest.csv")
    parser.add_argument("--include-excluded", action="store_true")
    parser.add_argument("--require-usable", action="store_true")
    parser.add_argument("--include-weak", action="store_true", help="keep weak/pseudo labels")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-fraction", type=float, default=0.7)
    parser.add_argument("--val-fraction", type=float, default=0.15)
    args = parser.parse_args()

    labels = load_labels(args.labels) if args.labels else {}
    rows = build_manifest_rows(
        args.input,
        json_files(args.input),
        labels,
        include_excluded=args.include_excluded,
        require_usable=args.require_usable,
    )
    if not args.include_weak:
        for row in rows:
            if row["emotion"] and row["label_source"] not in {"", "manual"}:
                row["emotion"] = ""
                row["label_source"] = ""
    if not rows:
        raise SystemExit("no attempts matched the filters")

    split_map = assign_participant_splits(
        [row["participant_id"] for row in rows],
        seed=args.seed,
        train_fraction=args.train_fraction,
        val_fraction=args.val_fraction,
    )
    for row in rows:
        row["split"] = split_map.get(row["participant_id"], "train")

    write_manifest(args.output, rows)
    summary = manifest_summary(rows)
    summary["split_counts"] = {
        split: sum(1 for row in rows if row["split"] == split) for split in ("train", "val", "test")
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"manifest: {args.output}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
