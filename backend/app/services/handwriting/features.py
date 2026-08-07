#!/usr/bin/env python3
"""Extract interpretable baseline features from a MindLine handwriting trace."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def percentile(values: list[float], ratio: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * ratio
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def stats(values: Iterable[float], digits: int = 4) -> dict[str, float | int | None]:
    numbers = [float(value) for value in values if math.isfinite(float(value))]
    if not numbers:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "median": None,
            "p90": None,
            "p95": None,
            "max": None,
            "mean": None,
            "std": None,
        }
    return {
        "count": len(numbers),
        "min": round(min(numbers), digits),
        "p10": round(percentile(numbers, 0.10), digits),
        "median": round(percentile(numbers, 0.50), digits),
        "p90": round(percentile(numbers, 0.90), digits),
        "p95": round(percentile(numbers, 0.95), digits),
        "max": round(max(numbers), digits),
        "mean": round(statistics.fmean(numbers), digits),
        "std": round(statistics.pstdev(numbers), digits),
    }


def load_points(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    points = payload.get("points")
    if not isinstance(points, list) or not points:
        raise ValueError("JSON中没有有效points数组")
    valid_points = [point for point in points if isinstance(point, dict)]
    valid_points.sort(key=lambda point: int(point.get("sequence", 0)))
    return payload, valid_points


def extract(payload: dict[str, Any], points: list[dict[str, Any]]) -> dict[str, Any]:
    strokes: dict[int, list[dict[str, Any]]] = {}
    for point in points:
        stroke_id = point.get("strokeId")
        if isinstance(stroke_id, int):
            strokes.setdefault(stroke_id, []).append(point)

    ordered_strokes = [
        sorted(stroke, key=lambda point: int(point.get("sequence", 0)))
        for _, stroke in sorted(strokes.items())
    ]

    within_intervals: list[float] = []
    pen_up_pauses: list[float] = []
    speeds: list[float] = []
    accelerations: list[float] = []
    stroke_lengths: list[float] = []
    active_pressures: list[float] = []
    tilt_x: list[float] = []
    tilt_y: list[float] = []
    x_norms: list[float] = []
    y_norms: list[float] = []
    zero_interval_count = 0
    total_path_length = 0.0

    previous_stroke_end: int | None = None
    for stroke in ordered_strokes:
        if not stroke:
            continue
        first_elapsed = stroke[0].get("elapsedMs")
        last_elapsed = stroke[-1].get("elapsedMs")
        if (
            previous_stroke_end is not None
            and isinstance(first_elapsed, int)
            and first_elapsed >= previous_stroke_end
        ):
            pen_up_pauses.append(float(first_elapsed - previous_stroke_end))
        if isinstance(last_elapsed, int):
            previous_stroke_end = last_elapsed

        stroke_length = 0.0
        previous_speed: float | None = None
        previous_speed_time: int | None = None
        for point in stroke:
            pressure = finite(point.get("pressure"))
            if pressure is not None and pressure > 0 and point.get("phase") != "up":
                active_pressures.append(pressure)
            tx = finite(point.get("tiltX"))
            ty = finite(point.get("tiltY"))
            if tx is not None:
                tilt_x.append(tx)
            if ty is not None:
                tilt_y.append(ty)
            xn = finite(point.get("xNorm"))
            yn = finite(point.get("yNorm"))
            if xn is not None:
                x_norms.append(xn)
            if yn is not None:
                y_norms.append(yn)

        for previous, current in zip(stroke, stroke[1:], strict=False):
            previous_time = previous.get("elapsedMs")
            current_time = current.get("elapsedMs")
            x1, y1 = finite(previous.get("x")), finite(previous.get("y"))
            x2, y2 = finite(current.get("x")), finite(current.get("y"))
            if (
                not isinstance(previous_time, int)
                or not isinstance(current_time, int)
                or current_time < previous_time
            ):
                continue
            interval = float(current_time - previous_time)
            within_intervals.append(interval)
            if interval == 0:
                zero_interval_count += 1
                continue
            if None in (x1, y1, x2, y2):
                continue
            distance = math.hypot(x2 - x1, y2 - y1)
            stroke_length += distance
            speed = distance / (interval / 1000.0)
            speeds.append(speed)
            if previous_speed is not None and previous_speed_time is not None:
                acceleration_dt = (current_time - previous_speed_time) / 1000.0
                if acceleration_dt > 0:
                    accelerations.append((speed - previous_speed) / acceleration_dt)
            previous_speed = speed
            previous_speed_time = current_time

        stroke_lengths.append(stroke_length)
        total_path_length += stroke_length

    elapsed_values = [
        point["elapsedMs"] for point in points if isinstance(point.get("elapsedMs"), int)
    ]
    task_duration_ms = max(elapsed_values) - min(elapsed_values) if len(elapsed_values) >= 2 else 0
    total_pause_ms = sum(pen_up_pauses)
    long_pauses = [pause for pause in pen_up_pauses if pause >= 500]

    bbox = None
    if x_norms and y_norms:
        width = max(x_norms) - min(x_norms)
        height = max(y_norms) - min(y_norms)
        bbox = {
            "minX": round(min(x_norms), 4),
            "maxX": round(max(x_norms), 4),
            "minY": round(min(y_norms), 4),
            "maxY": round(max(y_norms), 4),
            "width": round(width, 4),
            "height": round(height, 4),
            "area": round(width * height, 4),
        }

    warnings: list[str] = []
    if not active_pressures:
        warnings.append("没有有效落笔压力，压力相关特征必须禁用")
    elif max(active_pressures) - min(active_pressures) < 0.01:
        warnings.append("有效压力几乎不变化，可能不是设备真实压感")
    if within_intervals and percentile(within_intervals, 0.95) > 50:
        warnings.append("笔划内部采样间隔P95大于50ms，需要检查浏览器卡顿")
    if within_intervals and zero_interval_count / len(within_intervals) > 0.1:
        warnings.append("零毫秒采样点比例超过10%，后续重采样时需要合并")

    return {
        "featureVersion": "0.1.0",
        "sessionId": payload.get("sessionId"),
        "participantId": payload.get("participantId"),
        "taskType": payload.get("task", {}).get("type"),
        "device": {
            "pointerTypes": payload.get("device", {}).get("observedPointerTypes", []),
            "supportsPressure": payload.get("device", {}).get("supportsPressure"),
            "supportsTilt": payload.get("device", {}).get("supportsTilt"),
        },
        "counts": {
            "points": len(points),
            "strokes": len(ordered_strokes),
            "zeroIntervalPoints": zero_interval_count,
            "longPauseCount": len(long_pauses),
        },
        "timing": {
            "taskDurationMs": task_duration_ms,
            "totalPenUpPauseMs": round(total_pause_ms, 4),
            "penUpRatio": round(total_pause_ms / task_duration_ms, 4)
            if task_duration_ms > 0
            else None,
            "withinStrokeIntervalMs": stats(within_intervals),
            "betweenStrokePauseMs": stats(pen_up_pauses),
            "longPausesMs": stats(long_pauses),
        },
        "pressure": stats(active_pressures),
        "tiltX": stats(tilt_x),
        "tiltY": stats(tilt_y),
        "kinematics": {
            "totalPathLengthPx": round(total_path_length, 4),
            "strokeLengthPx": stats(stroke_lengths),
            "speedPxPerSecond": stats(speeds),
            "accelerationPxPerSecond2": stats(accelerations),
        },
        "geometry": {"normalizedBoundingBox": bbox},
        "labels": payload.get("selfReport", {}),
        "warnings": warnings,
        "limitations": [
            "速度使用浏览器CSS像素计算，跨设备比较前需要物理尺寸校准",
            "当前特征用于设备验证和个人纵向研究，不用于医学诊断",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="提取心迹AI笔迹基线特征")
    parser.add_argument("path", type=Path, help="采集器导出的轨迹JSON")
    parser.add_argument("-o", "--output", type=Path, help="可选的特征JSON输出路径")
    args = parser.parse_args()

    try:
        payload, points = load_points(args.path)
        result = extract(payload, points)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
