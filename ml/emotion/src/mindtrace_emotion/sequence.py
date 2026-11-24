"""Variable-length collector points -> fixed-length model channels."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

CHANNELS = ("dx", "dy", "dt_seconds", "pressure", "pen_state")
SEQUENCE_VERSION = "collector-sequence-v0.1"


def _finite(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    return number if math.isfinite(number) else math.nan


def _parse(points: list[dict[str, Any]], canvas: dict[str, Any] | None) -> dict[str, np.ndarray]:
    width = _finite((canvas or {}).get("width"))
    height = _finite((canvas or {}).get("height"))
    rows: list[tuple[int, float, float, float, float, bool, int, str]] = []
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
        down = point.get("penDown") is True or phase in {"down", "move"}
        pressure = _finite(point.get("pressure"))
        stroke = int(point.get("strokeId", 0) or 0)
        pointer = str(point.get("pointerType", "")).lower()
        seq = int(point.get("seq", order) or 0)
        rows.append((seq, x, y, timestamp, pressure, down, stroke, pointer))
    rows.sort(key=lambda row: row[0])
    return {
        "x": np.asarray([row[1] for row in rows], dtype=float),
        "y": np.asarray([row[2] for row in rows], dtype=float),
        "t": np.asarray([row[3] for row in rows], dtype=float),
        "pressure": np.asarray([row[4] for row in rows], dtype=float),
        "down": np.asarray([row[5] for row in rows], dtype=bool),
        "stroke": np.asarray([row[6] for row in rows], dtype=int),
        "pointer": np.asarray([row[7] for row in rows], dtype=object),
    }


def build_sequence(
    points: list[dict[str, Any]],
    canvas: dict[str, Any] | None = None,
    max_len: int = 512,
) -> dict[str, np.ndarray | int]:
    """Resample by elapsed time and return five channels plus masks.

    ``values`` has shape ``[length, 5]``; the PyTorch collator pads it.  The
    pressure mask is false when the attempt is not a validated dynamic-pen
    attempt, so unknown pressure is never treated as a measured zero.
    """
    if max_len < 2:
        raise ValueError("max_len must be at least 2")
    series = _parse(points, canvas)
    count = len(series["x"])
    pointer_pen = any(item == "pen" for item in series["pointer"].tolist())
    pressure = series["pressure"]
    down = series["down"]
    pressure_down = pressure[down & np.isfinite(pressure)]
    pressure_valid = bool(pointer_pen and pressure_down.size and np.ptp(pressure_down) >= 0.01)

    if count == 0:
        values = np.zeros((1, len(CHANNELS)), dtype=np.float32)
        mask = np.zeros((1, len(CHANNELS)), dtype=bool)
        return {
            "values": values,
            "feature_mask": mask,
            "stroke_boundary": np.asarray([True], dtype=bool),
            "length": 1,
            "pressure_valid": False,
            "version": SEQUENCE_VERSION,
        }

    t = np.maximum.accumulate(series["t"])
    x, y = series["x"], series["y"]
    if count >= 2 and t[-1] > t[0]:
        target_t = np.linspace(t[0], t[-1], max_len)
        x = np.interp(target_t, t, x)
        y = np.interp(target_t, t, y)
        if pressure_valid:
            pressure = np.interp(target_t, t, np.nan_to_num(pressure, nan=0.0))
        else:
            pressure = np.zeros(max_len, dtype=float)
        down = np.interp(target_t, t, down.astype(float)) >= 0.5
        stroke = np.rint(np.interp(target_t, t, series["stroke"].astype(float))).astype(int)
        t = target_t

    dx = np.zeros_like(x)
    dy = np.zeros_like(y)
    if len(x) > 1:
        dx[1:] = np.diff(x)
        dy[1:] = np.diff(y)
    dt = np.zeros_like(t)
    if len(t) > 1:
        dt[1:] = np.diff(t) / 1000.0
        dt[1:] = np.clip(dt[1:], 0.0, 10.0)
    values = np.column_stack(
        [
            dx,
            dy,
            dt,
            pressure if pressure_valid else np.zeros_like(t),
            down.astype(float),
        ]
    ).astype(np.float32)
    mask = np.ones_like(values, dtype=bool)
    if len(t) > 0:
        mask[0, 0:3] = False  # first point has no predecessor
        mask[:, 3] = pressure_valid
    boundary = np.zeros(len(t), dtype=bool)
    boundary[0] = True
    if len(t) > 1:
        boundary[1:] = stroke[1:] != stroke[:-1]
    values[~mask] = 0.0
    return {
        "values": values,
        "feature_mask": mask,
        "stroke_boundary": boundary,
        "length": int(len(values)),
        "pressure_valid": pressure_valid,
        "version": SEQUENCE_VERSION,
    }
