"""Optional, low-confidence ridge baseline for reproducible research."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MODEL_PATH = (
    REPO_ROOT / "research" / "handwriting" / "models" / "handwriting_ridge_v0.1.json"
)
TARGET_LABELS = {
    "stress_level": "压力自评估计",
    "mood_level": "心情自评估计",
    "sleep_quality": "睡眠自评估计",
}


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _pick(data: dict[str, Any], *path: str) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def flatten_features(features: dict[str, Any]) -> dict[str, float | None]:
    bbox = _pick(features, "geometry", "normalizedBoundingBox") or {}
    return {
        "point_count": _finite(_pick(features, "counts", "points")),
        "stroke_count": _finite(_pick(features, "counts", "strokes")),
        "duration_ms": _finite(_pick(features, "timing", "taskDurationMs")),
        "long_pause_count": _finite(_pick(features, "counts", "longPauseCount")),
        "pen_up_ratio": _finite(_pick(features, "timing", "penUpRatio")),
        "within_interval_p95_ms": _finite(
            _pick(features, "timing", "withinStrokeIntervalMs", "p95")
        ),
        "between_pause_median_ms": _finite(
            _pick(features, "timing", "betweenStrokePauseMs", "median")
        ),
        "between_pause_p95_ms": _finite(_pick(features, "timing", "betweenStrokePauseMs", "p95")),
        "pressure_mean": _finite(_pick(features, "pressure", "mean")),
        "pressure_std": _finite(_pick(features, "pressure", "std")),
        "tilt_x_mean": _finite(_pick(features, "tiltX", "mean")),
        "tilt_x_std": _finite(_pick(features, "tiltX", "std")),
        "tilt_y_mean": _finite(_pick(features, "tiltY", "mean")),
        "tilt_y_std": _finite(_pick(features, "tiltY", "std")),
        "stroke_length_mean_px": _finite(_pick(features, "kinematics", "strokeLengthPx", "mean")),
        "stroke_length_std_px": _finite(_pick(features, "kinematics", "strokeLengthPx", "std")),
        "speed_median_px_s": _finite(_pick(features, "kinematics", "speedPxPerSecond", "median")),
        "speed_std_px_s": _finite(_pick(features, "kinematics", "speedPxPerSecond", "std")),
        "bbox_width_norm": _finite(bbox.get("width")),
        "bbox_height_norm": _finite(bbox.get("height")),
        "bbox_area_norm": _finite(bbox.get("area")),
    }


KNOWN_FEATURE_NAMES = frozenset(flatten_features({}))
# A model artifact may add one binary dummy per task type; everything else must be known.
TASK_FEATURE_PREFIX = "task_"


def _is_known_feature(name: Any) -> bool:
    return isinstance(name, str) and (
        name in KNOWN_FEATURE_NAMES or name.startswith(TASK_FEATURE_PREFIX)
    )


def _is_finite_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def clamp_score(value: float) -> float:
    """Clamp to the 1-5 self-report range; a non-finite estimate degrades to the midpoint."""
    if not math.isfinite(value):
        return 3.0
    return round(max(1.0, min(5.0, value)), 2)


class HandwritingBaselinePredictor:
    """Loads a generated artifact without exposing participant data in responses."""

    def __init__(self, model_path: str | Path | None = None) -> None:
        configured = model_path or os.getenv("HANDWRITING_MODEL_PATH")
        if configured:
            candidate = Path(configured).expanduser()
            # Resolve relative overrides against the repository, not the current directory,
            # so the model is found no matter where the process was started.
            self.path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
        else:
            self.path = DEFAULT_MODEL_PATH
        self.artifact: dict[str, Any] | None = None
        self.error: str | None = None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            self._validate(value)
            self.artifact = value
        except FileNotFoundError:
            self.error = "模型文件不存在；已仅输出客观特征"
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            self.error = f"模型文件不可用：{type(error).__name__}"

    @staticmethod
    def _validate(artifact: Any) -> None:
        if not isinstance(artifact, dict):
            raise ValueError("artifact must be an object")
        names = artifact["featureNames"]
        means = artifact["featureMeans"]
        scales = artifact["featureScales"]
        if not isinstance(names, list) or not names:
            raise ValueError("featureNames must be a non-empty list")
        if not (len(names) == len(means) == len(scales)):
            raise ValueError("feature metadata length mismatch")
        unknown = [name for name in names if not _is_known_feature(name)]
        if unknown:
            # Without this the predictor silently imputes unknown features from the
            # means and still reports EXPERIMENTAL scores.
            raise ValueError(
                f"unknown feature names: {', '.join(str(name) for name in unknown[:5])}"
            )
        for label, values in (("featureMeans", means), ("featureScales", scales)):
            if not all(_is_finite_number(value) for value in values):
                raise ValueError(f"{label} must contain only finite numbers")
        for target in TARGET_LABELS:
            model = artifact["targets"][target]
            coefficients = model["coefficients"]
            if len(coefficients) != len(names):
                raise ValueError("coefficient length mismatch")
            if not _is_finite_number(model["intercept"]) or not all(
                _is_finite_number(value) for value in coefficients
            ):
                raise ValueError("model parameters must be finite numbers")

    def health(self) -> dict[str, Any]:
        artifact = self.artifact or {}
        return {
            "available": self.artifact is not None,
            "modelVersion": artifact.get("modelVersion"),
            "sampleCount": artifact.get("sampleCount", 0),
            "participantCount": artifact.get("participantCount", 0),
            "note": self.error,
        }

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        if self.artifact is None:
            return {
                "status": "UNAVAILABLE",
                "confidenceLevel": "NONE",
                "modelVersion": None,
                "scores": {},
                "warning": self.error,
            }

        artifact = self.artifact
        flat = flatten_features(features)
        task_type = str(features.get("taskType") or "")
        values: list[float] = []
        for index, name in enumerate(artifact["featureNames"]):
            if name.startswith("task_"):
                raw = 1.0 if task_type == name.removeprefix("task_") else 0.0
            else:
                raw = flat.get(name)
                if raw is None:
                    raw = float(artifact["featureMeans"][index])
            mean = float(artifact["featureMeans"][index])
            scale = float(artifact["featureScales"][index]) or 1.0
            values.append((float(raw) - mean) / scale)

        scores: dict[str, Any] = {}
        for target, label in TARGET_LABELS.items():
            model = artifact["targets"][target]
            estimate = float(model["intercept"]) + sum(
                value * float(weight)
                for value, weight in zip(values, model["coefficients"], strict=False)
            )
            scores[target] = {"label": label, "value": clamp_score(estimate)}

        return {
            "status": "EXPERIMENTAL",
            "confidenceLevel": "LOW",
            "modelVersion": artifact.get("modelVersion"),
            "sampleCount": artifact.get("sampleCount", 0),
            "participantCount": artifact.get("participantCount", 0),
            "scores": scores,
            "warning": "小样本工程拟合，仅验证技术链路；不得用于心理评估、诊断或个体决策。",
        }
