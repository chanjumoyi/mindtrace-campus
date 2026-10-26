"""Explicit evidence gates; observed score ranges never establish provenance or permission."""

import json
import math
from pathlib import Path

from mindtrace_ml.data import sha256
from mindtrace_ml.emothaw import SVC_COLUMNS


def readiness(evidence_path=None, workbook=None):
    if evidence_path is None:
        return dict(
            status="blocked",
            reasons=[
                "written_authorization_pending",
                "mirror_scoring_history_unverified",
                "source_schema_unverified",
                "existing_exploration_review_pending",
            ],
            classification_enabled=False,
        )
    path = Path(evidence_path).resolve()
    evidence = json.loads(path.read_text(encoding="utf-8"))
    reasons = []
    for key in ("written_authorization", "mirror_scoring", "source_schema", "existing_exploration"):
        item = evidence.get(key, {})
        if (
            item.get("status") != "verified"
            or not item.get("reviewed_by")
            or not item.get("reviewed_at")
        ):
            reasons.append(key + "_unverified")
            continue
        document = item.get("document", {})
        target = Path(document.get("path", ""))
        target = target if target.is_absolute() else path.parent / target
        if (
            not document.get("sha256")
            or not target.is_file()
            or sha256(target) != document["sha256"]
        ):
            reasons.append(key + "_evidence_missing_or_changed")
    auth = evidence.get("written_authorization", {})
    if "supervised_training" not in auth.get("scope", []):
        reasons.append("supervised_training_not_authorized")
    scoring = evidence.get("mirror_scoring", {})
    if (
        scoring.get("instrument") != "I-DASS-42"
        or scoring.get("conversion") != "none"
        or workbook is None
        or not Path(workbook).is_file()
        or scoring.get("workbook_sha256") != sha256(workbook)
    ):
        reasons.append("mirror_workbook_scoring_not_verified")
    schema = evidence.get("source_schema", {})
    bounds = schema.get("pressure_range", [])
    if (
        schema.get("columns") != list(SVC_COLUMNS)
        or schema.get("time_unit") != "ms"
        or not schema.get("coordinate_units")
        or len(bounds) != 2
        or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in bounds
        )
        or not bounds[0] < bounds[1]
    ):
        reasons.append("source_units_not_verified")
    if evidence.get("classification_enabled", False) is not False:
        reasons.append("classification_not_in_scope")
    return dict(
        status="blocked" if reasons else "ready_for_preregistration",
        reasons=sorted(set(reasons)),
        classification_enabled=False,
        formal_training_executed=False,
    )


def require_ready(evidence_path=None, workbook=None):
    result = readiness(evidence_path, workbook)
    if result["status"] != "ready_for_preregistration":
        raise PermissionError("; ".join(result["reasons"]))
    return result
