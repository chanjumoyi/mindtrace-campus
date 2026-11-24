"""Read-only collector session inventory and manifest construction."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .features import FEATURE_NAMES, extract_attempt_features
from .labels import normalize_emotion

LABEL_COLUMNS = (
    "session_id",
    "attempt_id",
    "participant_id",
    "emotion",
    "label_source",
    "confidence",
    "annotator",
    "notes",
)


def json_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def load_session(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("session root is not an object")
    if not isinstance(payload.get("sessionId"), str) or not payload["sessionId"]:
        raise ValueError("missing sessionId")
    if not isinstance(payload.get("attempts"), list):
        raise ValueError("missing attempts")
    return payload


def image_estimate(attempt: dict[str, Any]) -> tuple[bool, int]:
    image = attempt.get("image")
    if not isinstance(image, dict):
        return False, 0
    data_url = image.get("dataUrl")
    if not isinstance(data_url, str) or ";base64," not in data_url:
        return True, 0
    encoded = data_url.split(";base64,", 1)[1].strip()
    return True, max(0, len(encoded) * 3 // 4)


def attempt_quality(attempt: dict[str, Any]) -> str:
    quality = attempt.get("quality")
    if isinstance(quality, dict):
        return str(quality.get("status", "unknown"))
    return "unknown"


def _relative(path: Path, root: Path) -> str:
    if root.is_file():
        return path.name
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def session_summary(path: Path, root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    attempts = [item for item in payload.get("attempts", []) if isinstance(item, dict)]
    images = [image_estimate(item) for item in attempts]
    relative = _relative(path, root)
    return {
        "path": relative,
        "schema_version": str(payload.get("schemaVersion", "")),
        "app_version": str(payload.get("appVersion", "")),
        "session_id": str(payload.get("sessionId", "")),
        "participant_id": str(payload.get("participantId", "")),
        "dataset_eligibility": str(payload.get("datasetEligibility", "")),
        "attempt_count": len(attempts),
        "image_count": sum(1 for present, _ in images if present),
        "image_bytes_estimate": sum(size for _, size in images),
        "attempt_quality": dict(Counter(attempt_quality(item) for item in attempts)),
    }


def scan_sessions(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    sessions: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    for path in json_files(root):
        try:
            payload = load_session(path)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            invalid.append({"path": str(path), "error": str(error)})
            continue
        sessions.append(session_summary(path, root, payload))
    return sessions, invalid


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    """Load a private label CSV keyed by session_id (or attempt_id)."""
    labels: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return labels
        missing = {"session_id", "emotion"} - set(reader.fieldnames)
        if missing:
            raise ValueError(f"label CSV missing columns: {sorted(missing)}")
        for line_number, row in enumerate(reader, 2):
            raw = (row.get("emotion") or "").strip()
            label = normalize_emotion(raw) if raw else None
            if raw and label is None:
                raise ValueError(f"line {line_number}: unknown emotion {raw!r}")
            key = (row.get("attempt_id") or "").strip() or (row.get("session_id") or "").strip()
            if not key:
                raise ValueError(f"line {line_number}: missing session_id/attempt_id")
            record = {
                "emotion": label,
                "label_source": (row.get("label_source") or ("manual" if label else "")).strip(),
                "confidence": (row.get("confidence") or "").strip(),
                "annotator": (row.get("annotator") or "").strip(),
                "notes": (row.get("notes") or "").strip(),
            }
            previous = labels.get(key)
            if previous and previous["emotion"] != record["emotion"]:
                raise ValueError(f"line {line_number}: conflicting duplicate label for {key}")
            labels[key] = record
    return labels


def _label_for(
    labels: dict[str, dict[str, Any]], session_id: str, attempt_id: str
) -> dict[str, Any]:
    return (
        labels.get(attempt_id)
        or labels.get(session_id)
        or {
            "emotion": None,
            "label_source": "",
            "confidence": "",
            "annotator": "",
            "notes": "",
        }
    )


def build_manifest_rows(
    root: Path,
    sessions: Iterable[Path],
    labels: dict[str, dict[str, Any]],
    *,
    include_excluded: bool = False,
    require_usable: bool = False,
    include_unlabeled: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sessions:
        try:
            payload = load_session(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        eligibility = str(payload.get("datasetEligibility", ""))
        if not include_excluded and eligibility == "excluded_test_record":
            continue
        session_id = str(payload.get("sessionId", ""))
        participant_id = str(payload.get("participantId", ""))
        relative = _relative(path, root)
        for index, attempt in enumerate(payload.get("attempts", [])):
            if not isinstance(attempt, dict):
                continue
            quality_status = attempt_quality(attempt)
            if require_usable and quality_status != "usable":
                continue
            attempt_id = str(attempt.get("attemptId", f"{session_id}-{index + 1}"))
            label = _label_for(labels, session_id, attempt_id)
            if label["emotion"] is None and not include_unlabeled:
                continue
            features = extract_attempt_features(attempt, attempt.get("canvas"))
            image_present, image_bytes = image_estimate(attempt)
            row: dict[str, Any] = {
                "session_id": session_id,
                "participant_id": participant_id,
                "attempt_id": attempt_id,
                "attempt_number": attempt.get("attemptNumber", index + 1),
                "task_id": str(attempt.get("taskId", "")),
                "task_title": str(attempt.get("taskTitle", "")),
                "quality_status": quality_status,
                "dataset_eligibility": eligibility,
                "schema_version": str(payload.get("schemaVersion", "")),
                "app_version": str(payload.get("appVersion", "")),
                "source_path": relative,
                "image_present": image_present,
                "image_bytes_estimate": image_bytes,
                "emotion": label["emotion"] or "",
                "label_source": label["label_source"],
                "label_confidence": label["confidence"],
                "annotator": label["annotator"],
                "notes": label["notes"],
            }
            for name in FEATURE_NAMES:
                value = features.get(name, math.nan)
                row[name] = "" if not math.isfinite(value) else round(float(value), 6)
            rows.append(row)
    return rows


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("manifest would be empty; check inputs and filters")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def manifest_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    participants = sorted({str(row["participant_id"]) for row in rows})
    labels = Counter(str(row["emotion"]) for row in rows if str(row["emotion"]).strip())
    return {
        "rows": len(rows),
        "participants": len(participants),
        "sessions": len({str(row["session_id"]) for row in rows}),
        "labeled_rows": sum(labels.values()),
        "unlabeled_rows": len(rows) - sum(labels.values()),
        "label_counts": dict(labels),
        "task_counts": dict(Counter(str(row["task_id"]) for row in rows)),
        "quality_counts": dict(Counter(str(row["quality_status"]) for row in rows)),
        "image_rows": sum(1 for row in rows if row.get("image_present") is True),
    }
