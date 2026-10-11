#!/usr/bin/env python3
"""Import trajectory/image ZIP bundles into the private handwriting dataset."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZipFile

STAMP_RE = re.compile(
    r"^(?P<participant>self-\d+)(?:_(?P<task>copy-v1|free-v1))?_(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d{3}Z)\.(?P<ext>json|png)$"
)
# participantId comes from the imported file body, so it may never be used as a path
# component until it matches this allowlist.
PARTICIPANT_RE = re.compile(r"^self-\d{1,6}$")
ARCHIVE_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
MIN_POINTS = 20
MIN_STROKES = 3
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


def parse_name(name: str) -> dict[str, Any] | None:
    match = STAMP_RE.match(Path(name).name)
    if not match:
        return None
    values = match.groupdict()
    values["datetime"] = datetime.strptime(values["stamp"], "%Y-%m-%dT%H-%M-%S-%fZ").replace(
        tzinfo=UTC
    )
    return values


def sample_id(participant: str, stamp: str, task_type: str) -> str:
    compact = stamp.replace("-", "").replace(":", "")
    task = "copy" if task_type == "copy_text" else "free"
    return f"sample-{participant}-{compact}-{task}"


def quality_status(point_count: int, stroke_count: int) -> str:
    """Keep the same vocabulary as import_handwriting_json.py."""
    return "passed" if point_count >= MIN_POINTS and stroke_count >= MIN_STROKES else "review"


def safe_target(root: Path, relative: Path) -> Path:
    """Resolve a private-data path and refuse anything that escapes the root."""
    resolved_root = root.resolve()
    target = (resolved_root / relative).resolve()
    if target != resolved_root and resolved_root not in target.parents:
        raise ValueError(f"导入目标超出私有数据目录：{relative}")
    return target


def archive_directory(root: Path, label: str) -> Path:
    """Return a single-level archive directory that cannot escape the private root."""
    if not ARCHIVE_LABEL_RE.fullmatch(label):
        raise ValueError(
            "archive-label 只能包含字母、数字、点、下划线和连字符，"
            "必须以字母或数字开头且长度不超过 64"
        )
    return safe_target(root, Path("source-archives") / label)


def copy_once(source: Path, destination: Path) -> None:
    """Copy a file, tolerating a re-import of an already archived archive."""
    if source.resolve() == destination.resolve():
        return
    shutil.copy2(source, destination)


def zip_entries(archive: ZipFile, extension: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for name in archive.namelist():
        parsed = parse_name(name)
        if parsed and parsed["ext"] == extension:
            parsed["name"] = name
            entries.append(parsed)
    return entries


def counts(payload: dict[str, Any]) -> tuple[int, int]:
    points = payload.get("points")
    points = points if isinstance(points, list) else []
    strokes = {
        point.get("strokeId")
        for point in points
        if isinstance(point, dict) and isinstance(point.get("strokeId"), int)
    }
    summary = payload.get("summary") or {}
    return (
        int(summary.get("pointCount") or len(points)),
        int(summary.get("strokeCount") or len(strokes)),
    )


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


def load_trajectory_payload(archive: ZipFile, item: dict[str, Any]) -> dict[str, Any]:
    """Load one trajectory and validate fields that are consumed during import."""
    try:
        payload = json.loads(archive.read(item["name"]).decode("utf-8"))
    except (KeyError, RuntimeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{item['name']} 不是有效的 UTF-8 JSON：{error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{item['name']} 不是有效的采集器轨迹 JSON 对象")
    for field in ("selfReport", "timing", "summary"):
        value = payload.get(field)
        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{item['name']} 的 {field} 必须是 JSON 对象")
    points = payload.get("points")
    if points is not None and not isinstance(points, list):
        raise ValueError(f"{item['name']} 的 points 必须是 JSON 数组")
    return payload


def validate_trajectory_entries(
    archive: ZipFile, entries: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], str, str]]:
    """Read and validate every trajectory before the importer writes any files."""
    validated: list[tuple[dict[str, Any], str, str]] = []
    for item in entries:
        payload = load_trajectory_payload(archive, item)
        participant = str(payload.get("participantId") or item["participant"])
        if not PARTICIPANT_RE.fullmatch(participant):
            raise ValueError(
                f"{item['name']} 的 participantId 非法（不得包含路径字符）：{participant!r}"
            )
        task = payload.get("task")
        task_type = str((task.get("type") if isinstance(task, dict) else None) or "unknown")
        validated.append((item, participant, task_type))
    return validated


def main() -> int:
    parser = argparse.ArgumentParser(description="导入心迹AI批量轨迹和预览图")
    parser.add_argument("trajectory_zip", type=Path)
    parser.add_argument("image_zip", type=Path)
    parser.add_argument("--private-root", type=Path, default=Path("research/handwriting/private"))
    parser.add_argument(
        "--archive-label",
        default=datetime.now(UTC).date().isoformat(),
        help="归档子目录名，默认使用当前 UTC 日期",
    )
    args = parser.parse_args()
    root = args.private_root.resolve()
    manifest_path = root / "manifests" / "sessions.csv"

    with (
        ZipFile(args.trajectory_zip) as trajectory_archive,
        ZipFile(args.image_zip) as image_archive,
    ):
        try:
            bad_trajectory = trajectory_archive.testzip()
        except RuntimeError as error:
            parser.error(f"无法读取轨迹压缩包（可能已加密）：{error}")
        if bad_trajectory:
            parser.error(f"轨迹压缩包包含损坏文件：{bad_trajectory}")
        try:
            bad_image = image_archive.testzip()
        except RuntimeError as error:
            parser.error(f"无法读取预览图压缩包（可能已加密）：{error}")
        if bad_image:
            parser.error(f"预览图压缩包包含损坏文件：{bad_image}")
        json_entries = zip_entries(trajectory_archive, "json")
        images = zip_entries(image_archive, "png")
        if not json_entries:
            parser.error(f"轨迹压缩包中没有符合命名规则的 JSON：{args.trajectory_zip}")
        nearest_images(json_entries, images)
        try:
            validated_entries = validate_trajectory_entries(trajectory_archive, json_entries)
            archive_dir = archive_directory(root, args.archive_label)
        except ValueError as error:
            parser.error(str(error))

        # Nothing under the private root is created until every archive member and
        # trajectory payload has passed validation.
        archive_dir.mkdir(parents=True, exist_ok=True)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        copy_once(args.trajectory_zip, archive_dir / args.trajectory_zip.name)
        copy_once(args.image_zip, archive_dir / args.image_zip.name)

        new_rows: list[dict[str, Any]] = []
        used_sample_ids: set[str] = set()
        for item, participant, task_type in validated_entries:
            payload = load_trajectory_payload(trajectory_archive, item)
            base_sid = sample_id(participant, item["stamp"], task_type)
            sid = base_sid
            suffix = 2
            while sid in used_sample_ids:
                sid = f"{base_sid}-{suffix}"
                suffix += 1
            used_sample_ids.add(sid)
            date = item["datetime"].date().isoformat()
            relative_dir = Path("raw") / participant / date / sid
            target_dir = safe_target(root, relative_dir)
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

            report = payload.get("selfReport") or {}
            timing = payload.get("timing") or {}
            point_count, stroke_count = counts(payload)
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
                    "point_count": point_count,
                    "stroke_count": stroke_count,
                    "quality_status": quality_status(point_count, stroke_count),
                    "pairing_method": pairing,
                    "data_issue": issue,
                }
            )

    old_rows: list[dict[str, str]] = []
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            old_rows = [row for row in csv.DictReader(handle) if row.get("sample_id")]
    new_ids = {row["sample_id"] for row in new_rows}
    # Normalize foreign rows to this script's columns so DictWriter cannot raise.
    combined = [
        {key: row.get(key, "") for key in FIELDS}
        for row in old_rows
        if row.get("sample_id") not in new_ids
    ] + new_rows
    combined.sort(key=lambda row: (row.get("started_at", ""), row["sample_id"]))
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, quoting=csv.QUOTE_ALL)
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
