"""Local, explainable handwriting analysis for the MindLine A module.

This module intentionally reports observable writing-behaviour indicators.  It
does not diagnose mental illness or infer personality from handwriting.
"""

from __future__ import annotations

import math
import uuid
from typing import Any

from .baseline import HandwritingBaselinePredictor
from .features import extract

MODEL_VERSION = "handwriting-observation-v0.2-local"
MIN_POINTS = 20
MIN_STROKES = 3
BASELINE_PREDICTOR = HandwritingBaselinePredictor()


class TraceValidationError(ValueError):
    """Raised when the collector trace cannot be analysed safely."""


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def validate_trace(trace: Any) -> list[dict[str, Any]]:
    if not isinstance(trace, dict):
        raise TraceValidationError("trace 必须是采集器导出的 JSON 对象")
    missing = [
        key
        for key in ("schemaVersion", "sessionId", "participantId", "task", "points")
        if key not in trace
    ]
    if missing:
        raise TraceValidationError(f"轨迹缺少必要字段: {', '.join(missing)}")
    points = trace.get("points")
    if not isinstance(points, list) or not points:
        raise TraceValidationError("trace.points 必须是非空数组")
    valid_points = [point for point in points if isinstance(point, dict)]
    if not valid_points:
        raise TraceValidationError("trace.points 中没有可用采样点")
    valid_points.sort(key=lambda point: int(point.get("sequence", 0)))
    return valid_points


def _quality(
    trace: dict[str, Any], points: list[dict[str, Any]], features: dict[str, Any]
) -> tuple[float, list[str]]:
    warnings: list[str] = list(features.get("warnings") or [])
    point_count = len(points)
    stroke_count = int(features["counts"]["strokes"])
    pointer_types = {str(point.get("pointerType", "unknown")) for point in points}
    invalid_norm = sum(
        1
        for point in points
        if (_number(point.get("xNorm")) is None or _number(point.get("yNorm")) is None)
        or not 0 <= float(point.get("xNorm", -1)) <= 1
        or not 0 <= float(point.get("yNorm", -1)) <= 1
    )

    score = 1.0
    if point_count < MIN_POINTS:
        score -= 0.45
        warnings.append(f"采样点少于 {MIN_POINTS} 个")
    if stroke_count < MIN_STROKES:
        score -= 0.35
        warnings.append(f"有效笔划少于 {MIN_STROKES} 个")
    if "pen" not in pointer_types:
        score -= 0.25
        warnings.append("未检测到 pointerType=pen，可能不是 Pencil 轨迹")
    if invalid_norm:
        score -= min(0.3, invalid_norm / point_count)
        warnings.append(f"存在 {invalid_norm} 个归一化坐标异常点")
    return _clamp(score), list(dict.fromkeys(warnings))


def _cv(metric: dict[str, Any]) -> float | None:
    mean = _number(metric.get("mean"))
    std = _number(metric.get("std"))
    if mean is None or std is None or abs(mean) < 1e-9:
        return None
    return abs(std / mean)


def analyse_trace(trace: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
    points = validate_trace(trace)
    features = extract(trace, points)
    quality, warnings = _quality(trace, points, features)
    request_id = request_id or str(uuid.uuid4())
    task = trace.get("task") if isinstance(trace.get("task"), dict) else {}
    writing_content = str(task.get("promptText") or "").strip()

    timing = features["timing"]
    speed = features["kinematics"]["speedPxPerSecond"]
    pressure = features["pressure"]
    pause_ratio = _number(timing.get("penUpRatio"))
    speed_cv = _cv(speed)
    pressure_cv = _cv(pressure)

    hesitation = None if pause_ratio is None else _clamp(pause_ratio / 0.45)
    rhythm = None if speed_cv is None else _clamp(speed_cv / 1.5)
    tension = None
    if pressure.get("count", 0) and _number(pressure.get("mean")) is not None:
        # Device-relative pressure indicator only; not a psychological score.
        tension = _clamp(float(pressure["mean"]))

    observations = [
        {
            "feature": "stroke_count",
            "description": f"本次记录包含 {features['counts']['strokes']} 个笔划、{features['counts']['points']} 个采样点。",
            "change": None,
        },
        {
            "feature": "pen_up_pause",
            "description": (
                f"抬笔间隔占总书写时长的 {pause_ratio:.1%}，长间隔 {features['counts']['longPauseCount']} 次。"
                if pause_ratio is not None
                else "当前轨迹不足以计算抬笔间隔比例。"
            ),
            "change": None,
        },
        {
            "feature": "writing_speed",
            "description": (
                f"轨迹速度中位数为 {speed['median']} px/s，变异系数为 {speed_cv:.3f}。"
                if speed_cv is not None
                else "当前轨迹不足以稳定计算速度变异。"
            ),
            "change": None,
        },
        {
            "feature": "pressure",
            "description": (
                f"有效压力均值为 {pressure['mean']}，压力变异系数为 {pressure_cv:.3f}。"
                if pressure_cv is not None
                else "设备未提供足够的有效压力变化，压力指标已降级。"
            ),
            "change": None,
        },
    ]

    status = "SUCCESS" if quality >= 0.6 else "INSUFFICIENT_DATA"
    experimental_prediction = BASELINE_PREDICTOR.predict(features)
    limitations = [
        "所有指标仅描述本次书写行为，不代表人格、心理状态或医学诊断。",
        "速度使用浏览器像素计算，跨设备比较前必须进行物理尺寸和采样率校准。",
        "尚无同一参与者的个人基线，因此 change 字段为空，不进行状态变化推断。",
        "压力指标依赖设备真实压感，仅可在同一设备、同一任务内谨慎比较。",
        experimental_prediction.get("warning"),
        *warnings,
    ]
    return {
        "requestId": request_id,
        "status": status,
        "writingContent": writing_content,
        "dataQuality": quality,
        "observations": observations,
        "stateScores": {
            "hesitation": hesitation,
            "rhythmInstability": rhythm,
            "writingTension": tension,
        },
        "experimentalPrediction": experimental_prediction,
        "confidence": _clamp(quality * 0.65),
        "limitations": list(dict.fromkeys(item for item in limitations if item)),
        "modelVersion": MODEL_VERSION,
        "features": features,
        "citations": [
            {
                "hypothesisId": "H009",
                "sourceTitle": "笔迹心理学",
                "pdfPage": "29-30",
                "usage": "先报告客观特征，再讨论解释；本接口不输出心理结论。",
            },
            {
                "hypothesisId": "H001",
                "sourceTitle": "笔迹心理学",
                "pdfPage": "30",
                "usage": "速度不可孤立解释，只保留为同任务、同设备下的观察量。",
            },
            {
                "hypothesisId": "H002",
                "sourceTitle": "笔迹心理学",
                "pdfPage": "62-64",
                "usage": "压力与速度需组合且设备压力需校准。",
            },
        ],
    }
