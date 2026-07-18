#!/usr/bin/env python3
"""Train and audit a small ridge-regression handwriting baseline."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


NUMERIC_FEATURES = [
    "point_count",
    "stroke_count",
    "duration_ms",
    "long_pause_count",
    "pen_up_ratio",
    "within_interval_p95_ms",
    "between_pause_median_ms",
    "between_pause_p95_ms",
    "pressure_mean",
    "pressure_std",
    "tilt_x_mean",
    "tilt_x_std",
    "tilt_y_mean",
    "tilt_y_std",
    "stroke_length_mean_px",
    "stroke_length_std_px",
    "speed_median_px_s",
    "speed_std_px_s",
    "bbox_width_norm",
    "bbox_height_norm",
    "bbox_area_norm",
]
TARGETS = ["stress_level", "mood_level", "sleep_quality"]


def number(value: str) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else np.nan
    except (TypeError, ValueError):
        return np.nan


def matrix(rows: list[dict[str, str]]) -> tuple[np.ndarray, list[str]]:
    values = [[number(row.get(name, "")) for name in NUMERIC_FEATURES] for row in rows]
    tasks = sorted({row["task_type"] for row in rows})
    task_names = [f"task_{task}" for task in tasks[1:]]
    encoded = [
        value_row + [1.0 if row["task_type"] == task else 0.0 for task in tasks[1:]]
        for row, value_row in zip(rows, values)
    ]
    return np.asarray(encoded, dtype=float), NUMERIC_FEATURES + task_names


def prepare(train_x: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    means = np.nanmean(train_x, axis=0)
    means = np.where(np.isfinite(means), means, 0.0)
    train = np.where(np.isnan(train_x), means, train_x)
    test = np.where(np.isnan(test_x), means, test_x)
    scales = np.std(train, axis=0)
    scales = np.where(scales < 1e-9, 1.0, scales)
    return (train - means) / scales, (test - means) / scales, means, scales


def ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> tuple[float, np.ndarray]:
    design = np.column_stack([np.ones(len(x)), x])
    penalty = np.eye(design.shape[1]) * alpha
    penalty[0, 0] = 0.0
    params = np.linalg.solve(design.T @ design + penalty, design.T @ y)
    return float(params[0]), params[1:]


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    error = predicted - actual
    return {
        "mae": round(float(np.mean(np.abs(error))), 4),
        "rmse": round(float(np.sqrt(np.mean(error**2))), 4),
    }


def evaluate(
    x: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    alpha: float,
) -> tuple[dict[str, float], dict[str, float]]:
    predictions = np.empty(len(y))
    mean_predictions = np.empty(len(y))
    for train, test in folds:
        train_x, test_x, _, _ = prepare(x[train], x[test])
        intercept, weights = ridge_fit(train_x, y[train], alpha)
        predictions[test] = np.clip(intercept + test_x @ weights, 1.0, 5.0)
        mean_predictions[test] = np.mean(y[train])
    return metrics(y, predictions), metrics(y, mean_predictions)


def grouped_folds(participants: list[str]) -> list[tuple[np.ndarray, np.ndarray]]:
    values = np.asarray(participants)
    return [
        (np.flatnonzero(values != participant), np.flatnonzero(values == participant))
        for participant in sorted(set(participants))
    ]


def sample_folds(size: int, seed: int = 20260717) -> list[tuple[np.ndarray, np.ndarray]]:
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(size)
    chunks = np.array_split(shuffled, 5)
    all_indices = np.arange(size)
    return [(np.setdiff1d(all_indices, test), test) for test in chunks]


def main() -> int:
    parser = argparse.ArgumentParser(description="训练并审计心迹AI可解释基线")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/handwriting-private/features/modeling_dataset_v0.1.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/handwriting-private/models")
    )
    parser.add_argument("--alpha", type=float, default=10.0)
    args = parser.parse_args()
    with args.dataset.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("collection_usable", "").lower() == "true"
            and all(row.get(target) for target in TARGETS)
        ]
    x, feature_names = matrix(rows)
    participants = [row["participant_id"] for row in rows]
    group_cv = grouped_folds(participants)
    random_cv = sample_folds(len(rows))

    evaluation: dict[str, Any] = {}
    models: dict[str, Any] = {}
    train_x, _, means, scales = prepare(x, x)
    for target in TARGETS:
        y = np.asarray([number(row[target]) for row in rows], dtype=float)
        group_result, group_mean = evaluate(x, y, group_cv, args.alpha)
        random_result, random_mean = evaluate(x, y, random_cv, args.alpha)
        intercept, weights = ridge_fit(train_x, y, args.alpha)
        evaluation[target] = {
            "leaveOneParticipantOut": group_result,
            "leaveOneParticipantOutMeanBaseline": group_mean,
            "randomFiveFoldLeakageProne": random_result,
            "randomFiveFoldMeanBaseline": random_mean,
        }
        models[target] = {
            "intercept": round(intercept, 8),
            "coefficients": [round(float(value), 8) for value in weights],
        }

    label_sets: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for row in rows:
        label_sets[row["participant_id"]].add(tuple(row[target] for target in TARGETS))
    fixed_participants = [key for key, values in label_sets.items() if len(values) == 1]
    artifact = {
        "modelVersion": "0.1.0-prototype",
        "modelType": "standardized ridge regression",
        "alpha": args.alpha,
        "sampleCount": len(rows),
        "participantCount": len(set(participants)),
        "featureNames": feature_names,
        "featureMeans": [round(float(value), 8) for value in means],
        "featureScales": [round(float(value), 8) for value in scales],
        "targets": models,
        "evaluation": evaluation,
        "leakageAudit": {
            "participantsWithOnlyOneLabelCombination": fixed_participants,
            "fixedParticipantCount": len(fixed_participants),
            "warning": "Most participants have one fixed label combination; random-fold scores can learn writer identity.",
        },
        "intendedUse": "competition prototype and pipeline validation only",
        "notFor": ["medical diagnosis", "crisis decisions", "claims of population generalization"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.output_dir / "handwriting_ridge_v0.1.json"
    model_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 笔迹基线模型评估 v0.1",
        "",
        f"- 样本：{len(rows)}",
        f"- 参与者：{len(set(participants))}",
        f"- 固定标签参与者：{len(fixed_participants)}/{len(set(participants))}",
        "- 正式指标：留一参与者交叉验证（LOPO）",
        "- 随机五折仅用于展示身份泄漏风险，不作为模型成绩。",
        "",
        "| 目标 | LOPO MAE | 均值基线 MAE | 随机五折 MAE（泄漏风险） |",
        "|---|---:|---:|---:|",
    ]
    labels = {"stress_level": "压力", "mood_level": "情绪", "sleep_quality": "睡眠"}
    for target in TARGETS:
        result = evaluation[target]
        lines.append(
            f"| {labels[target]} | {result['leaveOneParticipantOut']['mae']:.4f} | "
            f"{result['leaveOneParticipantOutMeanBaseline']['mae']:.4f} | "
            f"{result['randomFiveFoldLeakageProne']['mae']:.4f} |"
        )
    lines += [
        "",
        "## 结论",
        "",
        "该模型已经打通轨迹到分数的工程链路，但当前参与者和标签结构不足以证明泛化能力。",
        "产品输出必须使用“观察到的笔迹特征”和“建议进一步自评”的措辞，不得输出诊断结论。",
    ]
    report_path = args.output_dir / "evaluation_v0.1.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"model": str(model_path), "evaluation": evaluation}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
