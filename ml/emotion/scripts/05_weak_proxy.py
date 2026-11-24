#!/usr/bin/env python3
"""Diagnostic weak-label proxy for the current collector export.

This is **not** emotion classification.  The collector currently stores no
emotion labels; this script demonstrates what can and cannot be learned from
the questionnaire weak labels.  It is deliberately small and reports every
leave-one-participant-out prediction instead of a single headline score.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mindtrace_emotion.features import FEATURE_NAMES, extract_attempt_features
from mindtrace_emotion.sessions import json_files, load_session

ROOT = Path(__file__).resolve().parents[3]

try:
    from sklearn.dummy import DummyClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        f1_score,
        mean_absolute_error,
    )
    from sklearn.model_selection import LeaveOneGroupOut
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
except ImportError as error:  # pragma: no cover
    raise SystemExit("scikit-learn is required: install ml/emotion/requirements.txt") from error

PROXY_FEATURES = [
    "point_count",
    "duration_ms",
    "speed_median",
    "speed_std",
    "pressure_mean",
    "pressure_std",
    "bbox_area_norm",
    "between_pause_count",
    "within_pause_count_500ms",
]


def finite_mean(values: list[float]) -> float:
    usable = [value for value in values if isinstance(value, int | float) and math.isfinite(value)]
    return float(np.mean(usable)) if usable else math.nan


def session_row(path: Path) -> dict | None:
    payload = load_session(path)
    if str(payload.get("datasetEligibility", "")) == "excluded_test_record":
        return None
    questionnaire = payload.get("questionnaire") or {}
    derived = questionnaire.get("derived") or {}
    quality = questionnaire.get("quality") or {}
    instrument = str(questionnaire.get("instrumentId", ""))
    raw_total = derived.get("rawTotal")
    symptom = derived.get("symptomSumS")
    if instrument == "WHO_5":
        try:
            raw_total = int(raw_total)
        except (TypeError, ValueError):
            return None
        below = derived.get("belowCutoff")
        below = bool(below) if isinstance(below, bool) else raw_total < 13
        target = "who5_below_cutoff"
        label = int(below)
    elif instrument == "MINDTRACE_RECENT_STATE_18":
        try:
            symptom = int(symptom)
        except (TypeError, ValueError):
            return None
        target = "mrs_symptom_high"
        label = int(symptom >= 32)
    else:
        return None

    attempts = [item for item in payload.get("attempts", []) if isinstance(item, dict)]
    copy_attempts = [
        item for item in attempts if "COPY_SENTENCE_REPEAT" in str(item.get("taskId", ""))
    ]
    selected = copy_attempts or attempts[:1]
    features = [extract_attempt_features(item, item.get("canvas")) for item in selected]
    if not features:
        return None
    values = {name: finite_mean([feature[name] for feature in features]) for name in FEATURE_NAMES}
    quality_summary = payload.get("qualitySummary") or {}
    row = {
        "session_id": str(payload.get("sessionId", "")),
        "participant_id": str(payload.get("participantId", "")),
        "schema_version": str(payload.get("schemaVersion", "")),
        "instrument": instrument,
        "dataset_eligibility": str(payload.get("datasetEligibility", "")),
        "record_status": str(quality.get("recordStatus", "")),
        "qc_flags": "|".join(str(flag) for flag in quality.get("qcFlags", [])),
        "raw_total": raw_total if instrument == "WHO_5" else None,
        "symptom_sum": symptom if instrument != "WHO_5" else None,
        "target": target,
        "label": label,
        "attempts_used": len(selected),
        "usable_attempts": quality_summary.get("usableAttempts"),
        "partial_attempts": quality_summary.get("partialAttempts"),
        "invalid_attempts": quality_summary.get("invalidAttempts"),
    }
    for name in PROXY_FEATURES:
        row[name] = values.get(name, math.nan)
    return row


def evaluate(frame: pd.DataFrame, target_name: str, output: Path) -> dict:
    subset = frame[frame["target"] == target_name].dropna(subset=["label"]).copy()
    if subset.empty:
        return {"target": target_name, "status": "no_rows"}
    classes = sorted(subset["label"].unique().tolist())
    result: dict = {
        "target": target_name,
        "rows": len(subset),
        "participants": int(subset["participant_id"].nunique()),
        "class_counts": {
            str(key): int(value) for key, value in subset["label"].value_counts().items()
        },
        "features": PROXY_FEATURES,
    }
    if len(classes) < 2 or len(subset) < 4:
        result["status"] = "too_few_rows_or_classes"
        return result
    x = subset[PROXY_FEATURES].to_numpy(dtype=float)
    y = subset["label"].to_numpy(dtype=int)
    groups = subset["participant_id"].to_numpy()
    predictions = np.full(len(subset), -1, dtype=int)
    probabilities = np.full(len(subset), np.nan, dtype=float)
    folds = []
    for train_index, test_index in LeaveOneGroupOut().split(x, y, groups):
        if len(np.unique(y[train_index])) < 2:
            continue
        model = Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                ("scale", StandardScaler()),
                ("model", LogisticRegression(C=0.5, class_weight="balanced", max_iter=5000)),
            ]
        )
        model.fit(x[train_index], y[train_index])
        predictions[test_index] = model.predict(x[test_index])
        probabilities[test_index] = model.predict_proba(x[test_index])[:, 1]
        folds.append(
            {
                "held_out": str(groups[test_index][0]),
                "actual": int(y[test_index][0]),
                "predicted": int(predictions[test_index][0]),
                "probability_positive": float(probabilities[test_index][0]),
            }
        )
    mask = predictions >= 0
    if not mask.any():
        result["status"] = "no_evaluable_fold"
        return result
    truth, predicted = y[mask], predictions[mask]
    dummy = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("model", DummyClassifier(strategy="most_frequent")),
        ]
    ).fit(x, y)
    dummy_predicted = dummy.predict(x)
    result.update(
        {
            "status": "ok",
            "accuracy": float(accuracy_score(truth, predicted)),
            "macro_f1": float(f1_score(truth, predicted, average="macro", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
            "dummy_accuracy": float(accuracy_score(y, dummy_predicted)),
            "dummy_macro_f1": float(f1_score(y, dummy_predicted, average="macro", zero_division=0)),
            "folds": folds,
        }
    )

    # A trivial quality rule is a confound check: if "partial_record" alone
    # predicts the weak label, the model may be learning acquisition quality.
    quality_predicted = (subset["dataset_eligibility"] == "partial_record").to_numpy(dtype=int)
    result["quality_rule_accuracy"] = float(accuracy_score(y, quality_predicted))
    result["quality_rule_macro_f1"] = float(
        f1_score(y, quality_predicted, average="macro", zero_division=0)
    )
    result["eligibility_by_label"] = {
        str(int(label)): {
            str(key): int(value)
            for key, value in group["dataset_eligibility"].value_counts().items()
        }
        for label, group in subset.groupby("label")
    }
    result["usable_attempts_by_label"] = {
        str(int(label)): [float(value) for value in group["usable_attempts"].dropna().tolist()]
        for label, group in subset.groupby("label")
    }

    # Exact label permutation over all class-preserving assignments.  With 8
    # participants there are only C(8, 3) = 56 assignments.
    positive_count = int(y.sum())
    better = 0
    assignments = 0
    for combination in itertools.combinations(range(len(y)), positive_count):
        permuted = np.zeros(len(y), dtype=int)
        permuted[list(combination)] = 1
        permuted_predicted = np.full(len(y), -1, dtype=int)
        for train_index, test_index in LeaveOneGroupOut().split(x, permuted, groups):
            if len(np.unique(permuted[train_index])) < 2:
                continue
            model = Pipeline(
                [
                    ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                    ("scale", StandardScaler()),
                    ("model", LogisticRegression(C=0.5, class_weight="balanced", max_iter=5000)),
                ]
            ).fit(x[train_index], permuted[train_index])
            permuted_predicted[test_index] = model.predict(x[test_index])
        if (permuted_predicted < 0).any():
            continue
        assignments += 1
        if accuracy_score(permuted, permuted_predicted) >= result["accuracy"] - 1e-12:
            better += 1
    result["permutation_p_value"] = float(better / assignments) if assignments else None
    result["permutation_label_assignments"] = assignments

    # Continuous companion: ridge on the same rows, only for WHO-5 raw totals.
    if target_name == "who5_below_cutoff":
        raw = subset["raw_total"].to_numpy(dtype=float)
        ridge_predictions = np.full(len(subset), np.nan)
        mean_predictions = np.full(len(subset), np.nan)
        for train_index, test_index in LeaveOneGroupOut().split(x, raw, groups):
            model = Pipeline(
                [
                    ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                    ("scale", StandardScaler()),
                    ("model", Ridge(alpha=10.0)),
                ]
            )
            model.fit(x[train_index], raw[train_index])
            ridge_predictions[test_index] = model.predict(x[test_index])
            mean_predictions[test_index] = float(raw[train_index].mean())
        valid = np.isfinite(ridge_predictions) & np.isfinite(mean_predictions)
        result["ridge_raw_total_mae"] = float(
            mean_absolute_error(raw[valid], ridge_predictions[valid])
        )
        result["training_mean_raw_total_mae"] = float(
            mean_absolute_error(raw[valid], mean_predictions[valid])
        )
        result["ridge_predictions"] = [
            {"participant_id": str(participant), "actual": float(actual), "predicted": float(pred)}
            for participant, actual, pred in zip(
                groups[valid], raw[valid], ridge_predictions[valid], strict=True
            )
        ]
    pd.DataFrame(
        [
            {
                "participant_id": str(participant),
                "actual": int(actual),
                "predicted": int(pred),
                "probability_positive": float(prob),
            }
            for participant, actual, pred, prob in zip(
                groups[mask], truth, predicted, probabilities[mask], strict=True
            )
        ]
    ).to_csv(output / f"predictions-{target_name}.csv", index=False, encoding="utf-8-sig")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    output = args.output_dir or (
        ROOT / "ml/emotion/runs" / f"weak-proxy-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    )
    output.mkdir(parents=True, exist_ok=False)

    rows = []
    for path in json_files(args.input):
        try:
            row = session_row(path)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if row is not None:
            rows.append(row)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise SystemExit("no WHO-5 or MRS-18 sessions with usable questionnaire scores")
    frame.to_csv(output / "weak_labels.csv", index=False, encoding="utf-8-sig")
    results = [
        evaluate(frame, target, output) for target in ("who5_below_cutoff", "mrs_symptom_high")
    ]
    report = {
        "notice": "This is a questionnaire weak-label proxy, not emotion classification.",
        "rows": len(frame),
        "participants": int(frame["participant_id"].nunique()),
        "instruments": frame["instrument"].value_counts().to_dict(),
        "results": results,
    }
    (output / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"run: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
