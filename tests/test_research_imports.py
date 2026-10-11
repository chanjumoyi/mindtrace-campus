from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from research.handwriting.scripts.import_handwriting_bundle import (
    archive_directory,
    main,
)


def _zip(path: Path, members: dict[str, str]) -> None:
    with ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_archive_label_cannot_escape_private_root(tmp_path: Path) -> None:
    root = tmp_path / "private"

    with pytest.raises(ValueError, match="archive-label"):
        archive_directory(root, "../../outside-private")

    target = archive_directory(root, "2026-10-11_review")
    assert target == (root / "source-archives" / "2026-10-11_review").resolve()


def test_invalid_trajectory_is_rejected_before_any_private_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trajectory_zip = tmp_path / "trajectory.zip"
    image_zip = tmp_path / "images.zip"
    private_root = tmp_path / "private"
    member_name = "self-1_copy-v1_2026-10-11T10-00-00-000Z.json"
    _zip(trajectory_zip, {member_name: "not-json"})
    _zip(image_zip, {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "import_handwriting_bundle.py",
            str(trajectory_zip),
            str(image_zip),
            "--private-root",
            str(private_root),
        ],
    )

    with pytest.raises(SystemExit):
        main()

    assert not private_root.exists()


def test_invalid_participant_is_rejected_before_any_private_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trajectory_zip = tmp_path / "trajectory.zip"
    image_zip = tmp_path / "images.zip"
    private_root = tmp_path / "private"
    member_name = "self-1_copy-v1_2026-10-11T10-00-00-000Z.json"
    payload = {
        "participantId": "../../outside-private",
        "sessionId": "synthetic",
        "task": {"type": "copy_text"},
        "points": [],
    }
    _zip(trajectory_zip, {member_name: json.dumps(payload)})
    _zip(image_zip, {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "import_handwriting_bundle.py",
            str(trajectory_zip),
            str(image_zip),
            "--private-root",
            str(private_root),
        ],
    )

    with pytest.raises(SystemExit):
        main()

    assert not private_root.exists()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("selfReport", []),
        ("timing", "not-an-object"),
        ("summary", 42),
    ],
)
def test_invalid_structured_field_is_rejected_before_any_private_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid_value: object,
) -> None:
    trajectory_zip = tmp_path / "trajectory.zip"
    image_zip = tmp_path / "images.zip"
    private_root = tmp_path / "private"
    member_name = "self-1_copy-v1_2026-10-11T10-00-00-000Z.json"
    payload = {
        "participantId": "self-1",
        "sessionId": "synthetic",
        "task": {"type": "copy_text"},
        "points": [],
        field: invalid_value,
    }
    _zip(trajectory_zip, {member_name: json.dumps(payload)})
    _zip(image_zip, {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "import_handwriting_bundle.py",
            str(trajectory_zip),
            str(image_zip),
            "--private-root",
            str(private_root),
        ],
    )

    with pytest.raises(SystemExit):
        main()

    assert not private_root.exists()


def test_duplicate_basenames_are_imported_as_distinct_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trajectory_zip = tmp_path / "trajectory.zip"
    image_zip = tmp_path / "images.zip"
    private_root = tmp_path / "private"
    basename = "self-1_copy-v1_2026-10-11T10-00-00-000Z.json"
    first_payload = {
        "participantId": "self-1",
        "sessionId": "first-session",
        "task": {"type": "copy_text"},
        "points": [],
    }
    second_payload = {**first_payload, "sessionId": "second-session"}
    _zip(
        trajectory_zip,
        {
            f"first/{basename}": json.dumps(first_payload),
            f"second/{basename}": json.dumps(second_payload),
        },
    )
    _zip(image_zip, {})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "import_handwriting_bundle.py",
            str(trajectory_zip),
            str(image_zip),
            "--private-root",
            str(private_root),
            "--archive-label",
            "test-run",
        ],
    )

    assert main() == 0

    manifest_path = private_root / "manifests" / "sessions.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert len({row["sample_id"] for row in rows}) == 2
    assert len({row["raw_json"] for row in rows}) == 2
    imported_sessions = {
        json.loads((private_root / row["raw_json"]).read_text(encoding="utf-8"))["sessionId"]
        for row in rows
    }
    assert imported_sessions == {"first-session", "second-session"}
