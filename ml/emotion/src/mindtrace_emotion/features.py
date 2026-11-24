"""Attempt-level handcrafted features for handwriting emotion experiments.

The extractor is intentionally independent from ``mindtrace_ml.features``:
that module consumes the unified OUHD-L trajectory contract, while the
collector JSON stores browser points with ``xNorm``/``yNorm`` and ``phase``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

FEATURE_VERSION = "emotion-features-v0.1"

FEATURE_NAMES = (
    "point_count",
    "stroke_count",
    "duration_ms",
    "down_fraction",
    "path_length_norm",
    "bbox_width_norm",
    "bbox_height_norm",
    "bbox_area_norm",
    "speed_median",
    "speed_mean",
    "speed_std",
    "speed_p90",
    "sampling_interval_median_ms",
    "sampling_interval_p95_ms",
    "stroke_length_mean",
    "stroke_length_std",
    "between_pause_count",
    "between_pause_median_ms",
    "between_pause_p95_ms",
    "within_pause_count_500ms",
    "pressure_mean",
    "pressure_std",
    "pressure_range",
    "tilt_x_mean",
    "tilt_y_mean",
)


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _nanmean(values: np.ndarray) -> float:
    return float(np.nanmean(values)) if values.size and np.isfinite(values).any() else math.nan


def _nanstd(values: np.ndarray) -> float:
    return float(np.nanstd(values)) if values.size and np.isfinite(values).any() else math.nan


def _nanpercentile(values: np.ndarray, percentile: float) -> float:
    return (
        float(np.nanpercentile(values, percentile))
        if values.size and np.isfinite(values).any()
        else math.nan
    )


def _extract_series(
    points: list[dict[str, Any]], canvas: dict[str, Any] | None
) -> dict[str, np.ndarray]:
    width = _finite((canvas or {}).get("width"))
    height = _finite((canvas or {}).get("height"))
    rows: list[tuple[int, float, float, float, float, int, bool, str, str]] = []
    for order, point in enumerate(points):
        if not isinstance(point, dict):
            continue
        x = _finite(point.get("xNorm"))
        y = _finite(point.get("yNorm"))
        if not math.isfinite(x) and math.isfinite(width) and width > 0:
            x = _finite(point.get("x")) / width
        if not math.isfinite(y) and math.isfinite(height) and height > 0:
            y = _finite(point.get("y")) / height
        timestamp = _finite(point.get("elapsedMs"))
        if not math.isfinite(timestamp):
            timestamp = _finite(point.get("taskElapsedMs"))
        if not math.isfinite(x) or not math.isfinite(y) or not math.isfinite(timestamp):
            continue
        phase = str(point.get("phase", "")).lower()
        pen_down = point.get("penDown") is True or phase in {"down", "move"}
        pressure = _finite(point.get("pressure"))
        stroke_id = int(point.get("strokeId", 0) or 0)
        pointer_type = str(point.get("pointerType", "")).lower()
        sequence = int(point.get("seq", order) or 0)
        rows.append((sequence, x, y, timestamp, pressure, stroke_id, pen_down, pointer_type, phase))

    if not rows:
        empty = np.empty(0, dtype=float)
        return {
            "x": empty,
            "y": empty,
            "t": empty,
            "pressure": empty,
            "stroke": np.empty(0, dtype=int),
            "down": np.empty(0, dtype=bool),
            "pointer": np.empty(0, dtype=object),
        }
    rows.sort(key=lambda row: row[0])
    return {
        "x": np.asarray([row[1] for row in rows], dtype=float),
        "y": np.asarray([row[2] for row in rows], dtype=float),
        "t": np.asarray([row[3] for row in rows], dtype=float),
        "pressure": np.asarray([row[4] for row in rows], dtype=float),
        "stroke": np.asarray([row[5] for row in rows], dtype=int),
        "down": np.asarray([row[6] for row in rows], dtype=bool),
        "pointer": np.asarray([row[7] for row in rows], dtype=object),
    }


def _edge_arrays(series: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    t = np.maximum.accumulate(series["t"])
    dt = np.diff(t) / 1000.0
    distance = np.hypot(np.diff(series["x"]), np.diff(series["y"]))
    same_stroke = series["stroke"][1:] == series["stroke"][:-1]
    down_edge = series["down"][1:] & series["down"][:-1]
    valid_edge = same_stroke & down_edge & np.isfinite(dt) & (dt > 0)
    speed = np.full_like(dt, np.nan)
    speed[valid_edge] = distance[valid_edge] / dt[valid_edge]
    return {
        "t": t,
        "dt": dt,
        "distance": distance,
        "same_stroke": same_stroke,
        "down_edge": down_edge,
        "valid_edge": valid_edge,
        "speed": speed,
    }


def extract_attempt_features(
    attempt: dict[str, Any], canvas: dict[str, Any] | None = None
) -> dict[str, float]:
    """Return finite-or-NaN features for one collector attempt."""
    points = attempt.get("points") if isinstance(attempt, dict) else None
    if not isinstance(points, list):
        points = []
    series = _extract_series(points, canvas if canvas is not None else attempt.get("canvas"))
    values = {name: math.nan for name in FEATURE_NAMES}
    if len(series["x"]) == 0:
        return values

    edge = _edge_arrays(series)
    t, dt, distance = edge["t"], edge["dt"], edge["distance"]
    down = series["down"]
    stroke = series["stroke"]
    pressure = series["pressure"]
    values["point_count"] = float(len(series["x"]))
    values["stroke_count"] = float(len(set(stroke[down].tolist()))) if down.any() else 0.0
    values["duration_ms"] = float(t[-1] - t[0]) if len(t) > 1 else 0.0
    values["down_fraction"] = float(down.mean())
    values["path_length_norm"] = float(distance[edge["valid_edge"]].sum())
    values["bbox_width_norm"] = float(np.ptp(series["x"]))
    values["bbox_height_norm"] = float(np.ptp(series["y"]))
    values["bbox_area_norm"] = values["bbox_width_norm"] * values["bbox_height_norm"]

    speed = edge["speed"]
    values["speed_median"] = _nanpercentile(speed, 50)
    values["speed_mean"] = _nanmean(speed)
    values["speed_std"] = _nanstd(speed)
    values["speed_p90"] = _nanpercentile(speed, 90)

    positive_dt = dt[np.isfinite(dt) & (dt > 0)]
    values["sampling_interval_median_ms"] = (
        float(np.median(positive_dt) * 1000) if positive_dt.size else math.nan
    )
    values["sampling_interval_p95_ms"] = (
        float(np.percentile(positive_dt, 95) * 1000) if positive_dt.size else math.nan
    )

    stroke_lengths: list[float] = []
    for stroke_id in sorted(set(stroke[down].tolist())):
        mask = (stroke == stroke_id) & down
        selected = distance[
            (stroke[1:] == stroke_id) & (stroke[:-1] == stroke_id) & down[1:] & down[:-1]
        ]
        if selected.size:
            stroke_lengths.append(float(selected.sum()))
        elif np.count_nonzero(mask) > 1:
            stroke_lengths.append(0.0)
    values["stroke_length_mean"] = float(np.mean(stroke_lengths)) if stroke_lengths else math.nan
    values["stroke_length_std"] = float(np.std(stroke_lengths)) if stroke_lengths else math.nan

    # A stroke ends at its last down sample; the next stroke starts at the next
    # down sample.  Only explicit pen-up -> pen-down gaps count as between-stroke.
    boundaries = np.flatnonzero(np.r_[True, stroke[1:] != stroke[:-1]])
    pauses: list[float] = []
    within_pauses = 0
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=False):
        first = np.flatnonzero(down[start:end])
        if first.size == 0:
            continue
        previous_end = start + int(first[-1])
        next_start = end + int(np.flatnonzero(down[end:])[0]) if down[end:].any() else None
        if next_start is None:
            continue
        gap = t[next_start] - t[previous_end]
        if gap >= 0:
            pauses.append(float(gap))
    for index in np.flatnonzero(edge["same_stroke"] & edge["down_edge"]):
        if dt[index] >= 0.5:
            within_pauses += 1
    values["between_pause_count"] = float(len(pauses))
    values["between_pause_median_ms"] = float(np.median(pauses)) if pauses else math.nan
    values["between_pause_p95_ms"] = float(np.percentile(pauses, 95)) if pauses else math.nan
    values["within_pause_count_500ms"] = float(within_pauses)

    pointer_pen = any(item == "pen" for item in series["pointer"].tolist())
    pressure_down = pressure[down & np.isfinite(pressure)]
    pressure_valid = bool(pointer_pen and pressure_down.size and np.ptp(pressure_down) >= 0.01)
    if pressure_valid:
        values["pressure_mean"] = float(np.mean(pressure_down))
        values["pressure_std"] = float(np.std(pressure_down))
        values["pressure_range"] = float(np.ptp(pressure_down))

    tilt_x = np.asarray(
        [_finite(point.get("tiltX")) for point in points if isinstance(point, dict)], dtype=float
    )
    tilt_y = np.asarray(
        [_finite(point.get("tiltY")) for point in points if isinstance(point, dict)], dtype=float
    )
    values["tilt_x_mean"] = _nanmean(tilt_x)
    values["tilt_y_mean"] = _nanmean(tilt_y)
    return values
