#!/usr/bin/env python3
"""Import standalone collector JSON files into the ignored private dataset."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FIELDS = [
    "sample_id",
    "participant_id",
    "date",
    "task_type",
    "context_code",
    "stress_level",
    "mood_level",
    "sleep_quality",
    "note",
    "raw_json",
    "preview_image",
    "original_zip",
    "original_json",
    "original_image",
    "embedded_session_id",
    "started_at",
    "duration_ms",
    "point_count",
    "stroke_count",
    "quality_status",
    "pairing_method",
    "data_issue",
]


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("points"), list):
        raise ValueError(f"{path} 不是有效的采集器轨迹 JSON")
    return payload


def sample_row(path: Path, payload: dict[str, Any], root: Path) -> dict[str, str]:
    participant = str(payload.get("participantId") or "anonymous")
    timing = payload.get("timing") or {}
    started_at = timing.get("startedAt") or timing.get("createdAt") or datetime.now(UTC).isoformat()
    parsed = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
    date = parsed.date().isoformat()
    task_type = str((payload.get("task") or {}).get("type") or "unknown")
    suffix = "copy" if task_type == "copy_text" else "free"
    stamp = parsed.astimezone(UTC).strftime("%Y%m%dT%H%M%S%f")[:18] + "Z"
    sample_id = f"sample-{participant}-{stamp}-{suffix}"
    relative = Path("raw") / participant / date / sample_id / "trace.json"
    target = (root / relative).resolve()
    if root.resolve() not in target.parents:
        raise ValueError("导入目标超出私有数据目录")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    report = payload.get("selfReport") or {}
    points = payload["points"]
    strokes = {
        point.get("strokeId")
        for point in points
        if isinstance(point, dict) and isinstance(point.get("strokeId"), int)
    }
    return {
        "sample_id": sample_id,
        "participant_id": participant,
        "date": date,
        "task_type": task_type,
        "context_code": "unknown",
        "stress_level": str(report.get("stressLevel", "")),
        "mood_level": str(report.get("moodLevel", "")),
        "sleep_quality": str(report.get("sleepQuality", "")),
        "note": str(report.get("note", "")),
        "raw_json": relative.as_posix(),
        "preview_image": "",
        "original_zip": "",
        "original_json": path.name,
        "original_image": "",
        "embedded_session_id": str(payload.get("sessionId", "")),
        "started_at": str(started_at),
        "duration_ms": str(timing.get("durationMs", "")),
        "point_count": str(len(points)),
        "stroke_count": str(len(strokes)),
        "quality_status": "passed" if len(points) >= 20 and len(strokes) >= 3 else "review",
        "pairing_method": "standalone_json",
        "data_issue": "missing_preview",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导入独立笔迹 JSON 到私有数据集")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--private-root", type=Path, default=Path("research/handwriting/private"))
    args = parser.parse_args()
    root = args.private_root
    manifest = root / "manifests" / "sessions.csv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, str]] = []
    if manifest.exists():
        with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
    known = {(row.get("original_json"), row.get("embedded_session_id")) for row in existing}
    imported = 0
    for path in args.paths:
        payload = load(path)
        key = (path.name, str(payload.get("sessionId", "")))
        if key in known:
            print(f"跳过重复样本: {path.name}")
            continue
        row = sample_row(path, payload, root)
        existing.append(row)
        known.add(key)
        imported += 1
        print(f"已导入: {row['sample_id']}")
    with manifest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(existing)
    print(f"导入完成: 新增 {imported} 条，清单共 {len(existing)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
