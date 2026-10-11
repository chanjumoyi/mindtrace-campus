from __future__ import annotations

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
