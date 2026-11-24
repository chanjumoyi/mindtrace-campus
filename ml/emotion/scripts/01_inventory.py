#!/usr/bin/env python3
"""Read-only inventory of collector session JSON files.

Only aggregate counts are printed.  The full inventory, including private
paths and participant identifiers, is written under ``ml/emotion/data/`` which
is git-ignored.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mindtrace_emotion.labels import normalize_emotion
from mindtrace_emotion.sessions import load_labels, scan_sessions

ROOT = Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="directory or one session JSON")
    parser.add_argument("--output", type=Path, default=ROOT / "ml/emotion/data/inventory.json")
    parser.add_argument("--labels", type=Path, help="optional private label CSV")
    args = parser.parse_args()

    sessions, invalid = scan_sessions(args.input)
    schemas = Counter(session["schema_version"] for session in sessions)
    eligibility = Counter(session["dataset_eligibility"] for session in sessions)
    qualities = Counter()
    for session in sessions:
        qualities.update(session["attempt_quality"])
    summary = {
        "input": str(args.input),
        "files_seen": len(sessions) + len(invalid),
        "valid_sessions": len(sessions),
        "invalid_files": invalid,
        "participants": len({session["participant_id"] for session in sessions}),
        "sessions": len({session["session_id"] for session in sessions}),
        "attempts": sum(session["attempt_count"] for session in sessions),
        "images": sum(session["image_count"] for session in sessions),
        "image_bytes_estimate": sum(session["image_bytes_estimate"] for session in sessions),
        "schemas": dict(schemas),
        "dataset_eligibility": dict(eligibility),
        "attempt_quality": dict(qualities),
        "sessions_detail": sessions,
    }
    if args.labels and args.labels.is_file():
        labels = load_labels(args.labels)
        session_ids = {session["session_id"] for session in sessions}
        matching_keys = {key for key in labels if key in session_ids}
        summary["label_file"] = str(args.labels)
        summary["label_rows"] = len(labels)
        summary["label_keys_matching_sessions"] = len(matching_keys)
        summary["labeled_session_classes"] = dict(
            Counter(
                normalize_emotion(labels[key]["emotion"])
                for key in matching_keys
                if labels[key]["emotion"]
            )
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    printable = {key: value for key, value in summary.items() if key != "sessions_detail"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))
    print(f"private inventory: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
