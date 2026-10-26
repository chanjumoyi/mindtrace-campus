"""Read-only EMOTHAW mirror adapter. Raw scores/units are never inferred or converted."""

import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from mindtrace_ml.data import sha256, source_root

VERSION = "emothaw-adapter-v1"
HEADERS = (
    "Suject",
    "depression",
    "anxiety",
    "stress",
    "Database Collectors",
    "File Number user",
    "Directory",
)
SCORES = ("depression", "anxiety", "stress")
SVC_COLUMNS = ("x", "y", "source_time", "pen_state", "azimuth", "altitude", "pressure")
FILENAME = re.compile(
    r"^u(?P<user>\d+)s(?P<session>\d+)_hw(?P<task>\d+)(?P<variant>.*)\.svc$", re.I
)


def participant_key(directory, number):
    if directory not in ("Collection1", "Collection2"):
        raise ValueError("unknown collection")
    if isinstance(number, bool):
        raise ValueError("invalid participant number")
    value = float(number)
    if not math.isfinite(value) or value < 1 or value != int(value):
        raise ValueError("invalid participant number")
    return directory, int(value)


def label_rows(rows):
    if not rows or tuple(rows[0]) != HEADERS:
        raise ValueError("label workbook schema mismatch")
    labels = {}
    for index, row in enumerate(rows[1:], 2):
        if len(row) != len(HEADERS):
            raise ValueError("label row width mismatch")
        key = participant_key(str(row[6]).strip(), row[5])
        if key in labels:
            raise ValueError("duplicate composite label key")
        scores = []
        for raw in row[1:4]:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
                raise ValueError("invalid raw score")
            if raw < 0 or raw > 42:
                raise ValueError("raw score requires review; never auto-rescale")
            scores.append(raw)
        labels[key] = dict(
            excel_row=index,
            raw_scores=dict(zip(SCORES, scores, strict=True)),
            scoring_history="unverified",
            original_study_instrument="I-DASS-42",
            score_conversion="none",
            classification_enabled=False,
        )
    return labels


def read_labels(path):
    import xlrd

    book = xlrd.open_workbook(str(path), on_demand=True)
    try:
        if "Feuil1" not in book.sheet_names():
            raise ValueError("canonical label sheet missing")
        sheet = book.sheet_by_name("Feuil1")
        return label_rows([sheet.row_values(i) for i in range(sheet.nrows)])
    finally:
        book.release_resources()


def read_svc(path):
    lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        raise ValueError("empty trajectory")
    declared = int(lines[0].strip())
    if declared < 1:
        raise ValueError("invalid declared point count")
    rows = [line.split() for line in lines[1:] if line.strip()]
    if any(len(row) != 7 for row in rows):
        raise ValueError("malformed trajectory width")
    points = np.asarray([[float(v) for v in row] for row in rows], dtype=float).reshape(-1, 7)
    issues = []
    if len(points) != declared:
        issues.append("declared_count_mismatch")
    if len(points) < 2:
        issues.append("insufficient_points")
    if not np.isfinite(points[:, :6]).all() or np.isinf(points[:, 6]).any():
        issues.append("nonfinite_measurement")
    if not np.isin(points[:, 3], [0, 1]).all():
        issues.append("invalid_pen_state")
    if (np.diff(points[:, 2]) < 0).any():
        issues.append("reversed_time")
    return dict(
        points=points,
        pressure_valid=np.isfinite(points[:, 6]),
        declared_points=declared,
        point_count=len(points),
        issues=issues,
        duplicate_timestamps=int((np.diff(points[:, 2]) == 0).sum()),
        units=dict(
            x="source_units",
            y="source_units",
            time="unverified_source_ticks",
            pressure="source_units",
            epoch_ms=None,
        ),
    )


def _inside(path, root):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("path escapes canonical root")
    return resolved


def audit(root=None):
    """Use exactly one configured mirror, never concatenate other downloads."""
    mirror = Path(root or source_root("emothaw")).resolve()
    data = _inside(mirror / "extracted/DataEmothaw", mirror)
    workbook = _inside(data / "DASS_scores.xls", mirror)
    paths = sorted(data.rglob("*.svc"))
    notes = sorted(data.rglob("*.txt"))
    protected = [workbook, *paths, *notes]
    if not paths or not workbook.is_file():
        raise ValueError("canonical data not available")
    for path in protected:
        _inside(path, mirror)
    before = {p.relative_to(mirror).as_posix(): sha256(p) for p in protected}
    labels = read_labels(workbook)
    records, groups, hashes = [], defaultdict(list), defaultdict(list)
    participant_issues = {key: set() for key in labels}
    for path in paths:
        relative = path.relative_to(data)
        parts = relative.parts
        if (
            len(parts) != 4
            or not re.fullmatch(r"user\d+", parts[1])
            or not re.fullmatch(r"session\d+", parts[2])
        ):
            raise ValueError("unexpected canonical trajectory path")
        key = participant_key(parts[0], int(parts[1][4:]))
        if key not in labels:
            raise ValueError("trajectory directory without composite label key")
        session = int(parts[2][7:])
        name = FILENAME.fullmatch(path.name)
        if name is None:
            raise ValueError("unrecognized trajectory filename")
        task = int(name["task"])
        issues = []
        if int(name["user"]) != key[1] or int(name["session"]) != session:
            issues.append("filename_directory_identity_conflict")
        if task not in range(1, 8):
            issues.append("unexpected_task")
        digest = before[path.relative_to(mirror).as_posix()]
        row = dict(
            path=path.relative_to(mirror).as_posix(),
            participant=list(key),
            session=session,
            task=task,
            variant=name["variant"],
            sha256=digest,
            issues=issues,
            selected=False,
        )
        try:
            trajectory = read_svc(path)
            row.update(
                {k: v for k, v in trajectory.items() if k not in ("points", "pressure_valid")}
            )
            row["issues"] = sorted(set(issues + trajectory["issues"]))
            row["missing_pressure_points"] = int((~trajectory["pressure_valid"]).sum())
        except (ValueError, OverflowError, UnicodeError) as error:
            row["issues"] = sorted(set(issues + ["unparseable_trajectory"]))
            row["parse_error_type"] = type(error).__name__
        index = len(records)
        records.append(row)
        groups[(key, session, task)].append(index)
        hashes[digest].append(index)
        participant_issues[key].update(row["issues"])
    for (key, _session, _task), indices in groups.items():
        canonical = [i for i in indices if not records[i]["variant"]]
        if len(canonical) != 1:
            participant_issues[key].add("ambiguous_task_version")
            continue
        chosen = canonical[0]
        records[chosen]["selected"] = True
        for i in indices:
            if i != chosen:
                records[i]["disposition"] = (
                    "duplicate_copy"
                    if records[i]["sha256"] == records[chosen]["sha256"]
                    else "superseded_variant_pending_review"
                )
                if records[i]["sha256"] != records[chosen]["sha256"]:
                    participant_issues[key].add("revised_variant_pending_review")
    for indices in hashes.values():
        locations = {
            (tuple(records[i]["participant"]), records[i]["session"], records[i]["task"])
            for i in indices
        }
        if len(locations) > 1:
            for i in indices:
                participant_issues[tuple(records[i]["participant"])].add(
                    "content_duplicate_across_tasks_or_participants"
                )
    private_notes = []
    for path in notes:
        parts = path.relative_to(data).parts
        if len(parts) < 3 or not re.fullmatch(r"user\d+", parts[1]):
            raise ValueError("unassigned source note")
        key = participant_key(parts[0], int(parts[1][4:]))
        if key not in labels:
            raise ValueError("source note without participant label")
        participant_issues[key].add("source_note_requires_review")
        private_notes.append(
            dict(
                path=path.relative_to(mirror).as_posix(),
                participant=list(key),
                text=path.read_text(encoding="utf-8-sig"),
            )
        )
    participants = []
    for key, label in labels.items():
        chosen = [r for r in records if tuple(r["participant"]) == key and r["selected"]]
        if not chosen:
            participant_issues[key].add("missing_trajectory_directory")
        if {r["task"] for r in chosen} != set(range(1, 8)):
            participant_issues[key].add("missing_task")
        if len({r["session"] for r in chosen}) > 1:
            participant_issues[key].add("multiple_sessions_require_review")
        reasons = sorted(participant_issues[key])
        participants.append(
            dict(
                key=list(key),
                label=label,
                issues=reasons,
                internal_pipeline_eligible=not reasons,
                formal_supervision_eligible=False,
                selected_tasks=[r["path"] for r in chosen],
            )
        )
    unchanged = all(sha256(mirror / name) == digest for name, digest in before.items())
    if not unchanged:
        raise RuntimeError("canonical source changed during read-only audit")
    counts = Counter(reason for p in participants for reason in p["issues"])
    summary = dict(
        status="passed",
        adapter_version=VERSION,
        canonical_roots_read=1,
        original_files_unchanged=True,
        label_rows=len(labels),
        trajectory_files=len(records),
        selected_task_candidates=sum(r["selected"] for r in records),
        duplicate_content_groups=sum(len(v) > 1 for v in hashes.values()),
        internal_pipeline_eligible_participants=sum(
            p["internal_pipeline_eligible"] for p in participants
        ),
        review_required_participants=sum(bool(p["issues"]) for p in participants),
        participant_issue_counts=dict(sorted(counts.items())),
        score_conversion="none",
        classification_enabled=False,
        formal_training_status="blocked",
        formal_experiments_executed=0,
        formal_training_reminder="还未展开正式训练",
        blockers=[
            "written_authorization_pending",
            "mirror_scoring_history_unverified",
            "source_units_unverified",
        ],
        existing_exploration_status="materials_not_located_no_new_analysis",
    )
    return dict(
        summary=summary,
        records=records,
        participants=participants,
        source_hashes=before,
        source_notes=private_notes,
        source="emothaw",
        canonical_root=str(mirror),
        svc_columns=SVC_COLUMNS,
    )
