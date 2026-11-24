#!/usr/bin/env python3
"""Participant-grouped baseline for handwriting emotion classification.

This is the first model you should run.  It is fast, interpretable enough to
debug label leakage, and tells you whether the trajectory features carry any
signal before spending GPU time on a sequence model.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mindtrace_emotion.features import FEATURE_NAMES
from mindtrace_emotion.labels import TAXONOMY_VERSION, normalize_emotion

ROOT = Path(__file__).resolve().parents[3]

try:
    from sklearn.compose import ColumnTransformer
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
    )
    from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, StratifiedGroupKFold
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.semi_supervised import SelfTrainingClassifier
except ImportError as error:  # pragma: no cover - dependency check
    raise SystemExit(
        "scikit-learn is required: install ml/emotion/requirements.txt in ml/.venv"
    ) from error


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, list(FEATURE_NAMES)),
            ("task", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["task_id"]),
        ]
    )


def build_model(model_name: str, seed: int):
    if model_name == "logreg":
        return LogisticRegression(max_iter=5000, class_weight="balanced", random_state=seed)
    if model_name == "random-forest":
        return RandomForestClassifier(
            n_estimators=400,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            random_state=seed,
            n_jobs=-1,
        )
    raise ValueError(f"unknown model: {model_name}")


def build_pipeline(model_name: str, seed: int) -> Pipeline:
    return Pipeline(
        [("preprocess", build_preprocessor()), ("model", build_model(model_name, seed))]
    )


def folds_for(groups: np.ndarray, scheme: str, seed: int):
    unique = np.unique(groups)
    if len(unique) < 2:
        raise SystemExit("at least two participants are required for grouped validation")
    if scheme == "loso":
        yield from LeaveOneGroupOut().split(np.zeros(len(groups)), groups=groups)
        return
    n_splits = min(5, len(unique))
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    try:
        yield from splitter.split(np.zeros(len(groups)), np.zeros(len(groups)), groups=groups)
    except ValueError:
        yield from GroupKFold(n_splits=n_splits).split(np.zeros(len(groups)), groups=groups)


def clean_metrics(truth: list[int], predicted: list[int], classes: list[str]) -> dict:
    labels = list(range(len(classes)))
    report = classification_report(
        truth,
        predicted,
        labels=labels,
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_f1": float(
            f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)
        ),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "per_class": {
            name: {
                "precision": float(report[name]["precision"]),
                "recall": float(report[name]["recall"]),
                "f1": float(report[name]["f1-score"]),
                "support": int(report[name]["support"]),
            }
            for name in classes
        },
        "confusion_matrix": confusion_matrix(truth, predicted, labels=labels).tolist(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="default: ml/emotion/runs/baseline-<UTC timestamp>",
    )
    parser.add_argument("--cv", choices=("loso", "group5"), default="group5")
    parser.add_argument("--model", choices=("logreg", "random-forest"), default="logreg")
    parser.add_argument("--semi-supervised", action="store_true")
    parser.add_argument("--include-weak", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output = args.output_dir or (
        ROOT / "ml/emotion/runs" / f"baseline-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    )
    output.mkdir(parents=True, exist_ok=False)

    frame = pd.read_csv(args.manifest, encoding="utf-8-sig")
    frame["emotion"] = frame["emotion"].fillna("").map(normalize_emotion)
    frame["label_source"] = frame["label_source"].fillna("").astype(str)
    if not args.include_weak:
        frame = frame[frame["label_source"].isin(["", "manual"])]
    frame["participant_id"] = frame["participant_id"].astype(str)
    frame["task_id"] = frame["task_id"].fillna("unknown").astype(str)
    classes = sorted(frame["emotion"].dropna().unique().tolist())
    if len(classes) < 2:
        raise SystemExit("fewer than two emotion classes with labels; nothing to train")
    class_to_index = {name: index for index, name in enumerate(classes)}
    frame["label_index"] = frame["emotion"].map(class_to_index)
    labeled = frame[frame["emotion"].notna()].copy()
    if labeled.empty:
        raise SystemExit("no labeled rows")
    feature_columns = [*FEATURE_NAMES, "task_id"]

    groups = frame["participant_id"].to_numpy()
    prediction_rows: list[dict] = []
    fold_metrics: list[dict] = []
    dummy_metrics: list[dict] = []
    for fold, (train_index, test_index) in enumerate(folds_for(groups, args.cv, args.seed), 1):
        train = frame.iloc[train_index]
        test = frame.iloc[test_index]
        train_labeled = train[train["emotion"].notna()]
        if train_labeled["emotion"].nunique() < 2:
            continue
        test_labeled = test[test["emotion"].notna()]
        if test_labeled.empty:
            continue

        if args.semi_supervised:
            unlabeled_train = train[train["emotion"].isna()]
            train_all = pd.concat([train_labeled, unlabeled_train], ignore_index=True)
            y_train_all = np.concatenate(
                [
                    train_labeled["label_index"].to_numpy(dtype=int),
                    np.full(len(unlabeled_train), -1, dtype=int),
                ]
            )
            preprocessor = build_preprocessor()
            train_matrix = preprocessor.fit_transform(train_all[feature_columns])
            test_matrix = preprocessor.transform(test_labeled[feature_columns])
            estimator = SelfTrainingClassifier(
                build_model(args.model, args.seed),
                criterion="threshold",
                threshold=0.9,
                max_iter=10,
            )
            estimator.fit(train_matrix, y_train_all)
            predicted = estimator.predict(test_matrix)
            dummy = DummyClassifier(strategy="most_frequent")
            dummy.fit(
                preprocessor.transform(train_labeled[feature_columns]),
                train_labeled["label_index"].to_numpy(dtype=int),
            )
            dummy_predicted = dummy.predict(test_matrix)
        else:
            estimator = build_pipeline(args.model, args.seed)
            estimator.fit(
                train_labeled[feature_columns],
                train_labeled["label_index"].to_numpy(dtype=int),
            )
            predicted = estimator.predict(test_labeled[feature_columns])
            dummy = build_pipeline(args.model, args.seed)
            dummy.set_params(model=DummyClassifier(strategy="most_frequent"))
            dummy.fit(
                train_labeled[feature_columns],
                train_labeled["label_index"].to_numpy(dtype=int),
            )
            dummy_predicted = dummy.predict(test_labeled[feature_columns])

        truth = test_labeled["label_index"].to_numpy(dtype=int)
        fold_metrics.append(clean_metrics(truth.tolist(), predicted.tolist(), classes))
        dummy_metrics.append(clean_metrics(truth.tolist(), dummy_predicted.tolist(), classes))
        for row, predicted_index in zip(test_labeled.itertuples(), predicted, strict=True):
            prediction_rows.append(
                {
                    "fold": fold,
                    "session_id": row.session_id,
                    "participant_id": row.participant_id,
                    "attempt_id": row.attempt_id,
                    "task_id": row.task_id,
                    "emotion": row.emotion,
                    "predicted": classes[int(predicted_index)],
                    "label_source": row.label_source,
                }
            )

    if not fold_metrics:
        raise SystemExit("no fold had both training and test labels")
    pooled_truth = [class_to_index[row["emotion"]] for row in prediction_rows]
    pooled_predicted = [class_to_index[row["predicted"]] for row in prediction_rows]
    aggregate = clean_metrics(pooled_truth, pooled_predicted, classes)
    macro_f1 = [item["macro_f1"] for item in fold_metrics]
    dummy_f1 = [item["macro_f1"] for item in dummy_metrics]
    metrics = {
        "taxonomy_version": TAXONOMY_VERSION,
        "classes": classes,
        "cv": args.cv,
        "model": args.model,
        "semi_supervised": bool(args.semi_supervised),
        "rows_total": len(frame),
        "rows_labeled": len(labeled),
        "participants": int(frame["participant_id"].nunique()),
        "pooled": aggregate,
        "folds": fold_metrics,
        "dummy_folds": dummy_metrics,
        "macro_f1_mean": float(np.mean(macro_f1)),
        "macro_f1_std": float(np.std(macro_f1)),
        "dummy_macro_f1_mean": float(np.mean(dummy_f1)),
    }
    (output / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(prediction_rows).to_csv(
        output / "predictions.csv", index=False, encoding="utf-8-sig"
    )

    import joblib

    if args.semi_supervised:
        preprocessor = build_preprocessor()
        matrix = preprocessor.fit_transform(frame[feature_columns])
        y_all = frame["label_index"].fillna(-1).to_numpy(dtype=int)
        final_model = SelfTrainingClassifier(
            build_model(args.model, args.seed),
            criterion="threshold",
            threshold=0.9,
            max_iter=10,
        )
        final_model.fit(matrix, y_all)
        artifact = {
            "preprocessor": preprocessor,
            "model": final_model,
            "classes": classes,
            "feature_names": list(FEATURE_NAMES),
            "taxonomy_version": TAXONOMY_VERSION,
            "sequence": "handcrafted-attempt-features",
            "semi_supervised": True,
        }
    else:
        final = build_pipeline(args.model, args.seed)
        final.fit(labeled[feature_columns], labeled["label_index"].to_numpy(dtype=int))
        artifact = {
            "pipeline": final,
            "classes": classes,
            "feature_names": list(FEATURE_NAMES),
            "taxonomy_version": TAXONOMY_VERSION,
            "sequence": "handcrafted-attempt-features",
            "semi_supervised": False,
        }
    joblib.dump(artifact, output / "model.joblib")
    card = f"""# Handwriting emotion baseline

- Taxonomy: `{TAXONOMY_VERSION}` ({", ".join(classes)})
- Model: {args.model}; semi-supervised={args.semi_supervised}; CV={args.cv}
- Labeled rows: {len(labeled)}; participants: {frame["participant_id"].nunique()}
- Pooled macro-F1: {aggregate["macro_f1"]:.3f}
- Fold macro-F1: {metrics["macro_f1_mean"]:.3f} ± {metrics["macro_f1_std"]:.3f}
- Dummy macro-F1: {metrics["dummy_macro_f1_mean"]:.3f}

## Limitations

This is an exploratory research model, not a diagnostic tool. Handwriting
features do not establish a person's emotion or mental-health state. Random
splits leak writer identity; only participant-grouped results are reported.
"""
    (output / "model-card.md").write_text(card, encoding="utf-8")
    print(
        json.dumps(
            {
                key: metrics[key]
                for key in (
                    "rows_labeled",
                    "participants",
                    "pooled",
                    "macro_f1_mean",
                    "macro_f1_std",
                    "dummy_macro_f1_mean",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"run: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
