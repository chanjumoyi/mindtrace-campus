#!/usr/bin/env python3
"""Import trajectory/image ZIP bundles into the private handwriting dataset."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile


STAMP_RE = re.compile(
    r"^(?P<participant>self-\d+)(?:_(?P<task>copy-v1|free-v1))?_(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)\.(?P<ext>json|png)$"
)


def parse_name(name: str) -> dict[str, Any] | None:
    match = STAMP_RE.match(Path(name).name)
    if not match:
        return None
    values = match.groupdict()
    values["datetime"] = datetime.strptime(
        values["stamp"], "%Y-%m-%dT%H-%M-%S-%fZ"
    ).replace(tzinfo=timezone.utc)
    return values


def sample_id(participant: str, stamp: str, task_type: str) -> str:
    compact = stamp.replace("-", "").replace(":", "")
    task = "copy" if task_type == "copy_text" else "free"
    return f"sample-{participant}-{compact}-{task}"


def nearest_images(json_entries: list[dict[str, Any]], images: list[dict[str, Any]]) -> None:
    unused = set(range(len(images)))
    for item in sorted(json_entries, key=lambda value: value["datetime"]):
        candidates = [
            (abs((images[index]["datetime"] - item["datetime"]).total_seconds()), index)
            for index in unused
            if images[index]["participant"] == item["participant"]
        ]
        if not candidates:
            item["image"] = None
            continue
        delta, index = min(candidates)
        if delta <= 6:
            item["image"] = images[index]
            item["pair_delta_seconds"] = round(delta, 3)
            unused.remove(index)
        else:
            item["image"] = None


def main() -> int:
    parser = argparse.ArgumentParser(description="导入心迹AI批量轨迹和预览图")
    parser.add_argument("trajectory_zip", type=Path)
    parser.add_argument("image_zip", type=Path)
    parser.add_argument(
        "--private-root", type=Path, default=Path("data/handwriting-private")
    )
    args = parser.parse_args()
    root = args.private_root.resolve()
    manifest_path = root / "manifests" / "sessions.csv"
    archive_dir = root / "source-archives" / "2026-07-17"
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.trajectory_zip, archive_dir / args.trajectory_zip.name)
    shutil.copy2(args.image_zip, archive_dir / args.image_zip.name)

    with ZipFile(args.trajectory_zip) as trajectory_archive, ZipFile(args.image_zip) as image_archive:
        json_entries: list[dict[str, Any]] = []
        for name in trajectory_archive.namelist():
            parsed = parse_name(name)
            if parsed and parsed["ext"] == "json":
                parsed["name"] = name
                json_entries.append(parsed)
        images: list[dict[str, Any]] = []
        for name in image_archive.namelist():
            parsed = parse_name(name)
            if parsed and parsed["ext"] == "png":
                parsed["name"] = name
                images.append(parsed)
        nearest_images(json_entries, images)

        new_rows: list[dict[str, Any]] = []
        for item in json_entries:
            payload = json.loads(trajectory_archive.read(item["name"]).decode("utf-8"))
            participant = str(payload.get("participantId") or item["participant"])
            task_type = str(payload.get("task", {}).get("type") or "unknown")
            sid = sample_id(participant, item["stamp"], task_type)
            date = item["datetime"].date().isoformat()
            relative_dir = Path("raw") / participant / date / sid
            target_dir = root / relative_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "trace.json").write_bytes(trajectory_archive.read(item["name"]))

            image = item.get("image")
            preview = ""
            original_image = ""
            pairing = "no_preview_within_6s"
            issue = "missing_preview"
            if image:
                (target_dir / "preview.png").write_bytes(image_archive.read(image["name"]))
                preview = (relative_dir / "preview.png").as_posix()
                original_image = Path(image["name"]).name
                pairing = f"nearest_export_timestamp_{item['pair_delta_seconds']}s"
                issue = ""

            report = payload.get("selfReport", {})
            timing = payload.get("timing", {})
            summary = payload.get("summary", {})
            new_rows.append(
                {
                    "sample_id": sid,
                    "participant_id": participant,
                    "date": date,
                    "task_type": task_type,
                    "context_code": "unknown",
                    "stress_level": report.get("stressLevel", ""),
                    "mood_level": report.get("moodLevel", ""),
                    "sleep_quality": report.get("sleepQuality", ""),
                    "note": report.get("note", ""),
                    "raw_json": (relative_dir / "trace.json").as_posix(),
                    "preview_image": preview,
                    "original_zip": args.trajectory_zip.name,
                    "original_json": Path(item["name"]).name,
                    "original_image": original_image,
                    "embedded_session_id": payload.get("sessionId", ""),
                    "started_at": timing.get("startedAt", ""),
                    "duration_ms": timing.get("durationMs", ""),
                    "point_count": summary.get("pointCount", len(payload.get("points", []))),
                    "stroke_count": summary.get("strokeCount", ""),
                    "quality_status": "pending_validation",
                    "pairing_method": pairing,
                    "data_issue": issue,
                }
            )

    old_rows: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            old_rows = list(csv.DictReader(handle))
    new_ids = {row["sample_id"] for row in new_rows}
    combined = [row for row in old_rows if row["sample_id"] not in new_ids] + new_rows
    combined.sort(key=lambda row: (row.get("started_at", ""), row["sample_id"]))
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(new_rows[0]))
        writer.writeheader()
        writer.writerows(combined)
    print(
        json.dumps(
            {
                "imported": len(new_rows),
                "total": len(combined),
                "pairedPreviews": sum(bool(row["preview_image"]) for row in new_rows),
                "missingPreviews": sum(not bool(row["preview_image"]) for row in new_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
