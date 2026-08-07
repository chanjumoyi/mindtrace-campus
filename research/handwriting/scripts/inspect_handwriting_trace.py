#!/usr/bin/env python3
"""Inspect a MindLine online-handwriting trace without external dependencies."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("根节点必须是JSON对象")
    return payload


def analyse(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required = [
        "schemaVersion",
        "sessionId",
        "participantId",
        "task",
        "device",
        "canvas",
        "timing",
        "summary",
        "points",
    ]
    for key in required:
        if key not in payload:
            errors.append(f"缺少必需字段：{key}")

    points = payload.get("points", [])
    if not isinstance(points, list):
        errors.append("points必须是数组")
        points = []

    sequences: list[int] = []
    stroke_ids: set[int] = set()
    pointer_types: set[str] = set()
    pressures: list[float] = []
    tilt_x: list[float] = []
    tilt_y: list[float] = []
    elapsed: list[int] = []
    invalid_coordinates = 0

    for index, point in enumerate(points):
        if not isinstance(point, dict):
            errors.append(f"points[{index}]不是对象")
            continue
        sequence = point.get("sequence")
        if isinstance(sequence, int):
            sequences.append(sequence)
        else:
            errors.append(f"points[{index}].sequence不是整数")
        stroke_id = point.get("strokeId")
        if isinstance(stroke_id, int):
            stroke_ids.add(stroke_id)
        pointer_types.add(str(point.get("pointerType", "unknown")))

        pressure = finite_number(point.get("pressure"))
        if pressure is not None:
            pressures.append(pressure)
        tx = finite_number(point.get("tiltX"))
        ty = finite_number(point.get("tiltY"))
        if tx is not None:
            tilt_x.append(tx)
        if ty is not None:
            tilt_y.append(ty)

        elapsed_ms = point.get("elapsedMs")
        if isinstance(elapsed_ms, int):
            elapsed.append(elapsed_ms)
        x_norm = finite_number(point.get("xNorm"))
        y_norm = finite_number(point.get("yNorm"))
        if x_norm is None or y_norm is None or not 0 <= x_norm <= 1 or not 0 <= y_norm <= 1:
            invalid_coordinates += 1

    if sequences and sequences != sorted(sequences):
        errors.append("sequence没有按递增顺序排列")
    if len(sequences) != len(set(sequences)):
        errors.append("sequence存在重复值")

    intervals = [
        current - previous
        for previous, current in zip(elapsed, elapsed[1:], strict=False)
        if current >= previous
    ]
    negative_intervals = sum(
        1 for previous, current in zip(elapsed, elapsed[1:], strict=False) if current < previous
    )
    if negative_intervals:
        errors.append(f"发现{negative_intervals}个倒序时间点")
    if len(points) < 20:
        warnings.append("采样点少于20，暂不适合特征提取")
    if len(stroke_ids) < 3:
        warnings.append("笔划少于3，暂不适合导出为有效样本")
    if "pen" not in pointer_types:
        warnings.append("没有观察到pointerType=pen，可能未识别Huawei Pencil")
    if not pressures:
        warnings.append("没有可用pressure数据")
    elif max(pressures) - min(pressures) < 0.01:
        warnings.append("pressure几乎没有变化，浏览器可能未暴露真实压感")
    if invalid_coordinates:
        warnings.append(f"发现{invalid_coordinates}个归一化坐标异常点")

    return {
        "schemaVersion": payload.get("schemaVersion"),
        "sessionId": payload.get("sessionId"),
        "participantId": payload.get("participantId"),
        "taskType": nested(payload, "task", "type"),
        "pointCount": len(points),
        "strokeCount": len(stroke_ids),
        "pointerTypes": sorted(pointer_types),
        "pressure": describe(pressures),
        "tiltX": describe(tilt_x),
        "tiltY": describe(tilt_y),
        "sampleIntervalMs": describe(intervals),
        "invalidCoordinateCount": invalid_coordinates,
        "errors": errors,
        "warnings": warnings,
        "usableForDeviceCheck": (not errors and len(points) >= 20 and len(stroke_ids) >= 3),
    }


def describe(values: list[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "std": None}
    numeric = [float(value) for value in values]
    return {
        "count": len(numeric),
        "min": round(min(numeric), 4),
        "max": round(max(numeric), 4),
        "mean": round(statistics.fmean(numeric), 4),
        "std": round(statistics.pstdev(numeric), 4),
    }


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def print_metric(name: str, metric: dict[str, Any]) -> None:
    print(
        f"{name}：count={metric['count']} min={metric['min']} "
        f"max={metric['max']} mean={metric['mean']} std={metric['std']}"
    )


def print_human(report: dict[str, Any]) -> None:
    print(f"会话：{report['sessionId']}")
    print(f"参与者：{report['participantId']}")
    print(f"任务：{report['taskType']}")
    print(f"采样点：{report['pointCount']}")
    print(f"笔划：{report['strokeCount']}")
    print(f"输入类型：{', '.join(report['pointerTypes']) or '无'}")
    print_metric("压力", report["pressure"])
    print_metric("tiltX", report["tiltX"])
    print_metric("tiltY", report["tiltY"])
    print_metric("采样间隔(ms)", report["sampleIntervalMs"])
    print(f"设备验证可用：{'是' if report['usableForDeviceCheck'] else '否'}")
    if report["warnings"]:
        print("\n警告：")
        for warning in report["warnings"]:
            print(f"- {warning}")
    if report["errors"]:
        print("\n错误：")
        for error in report["errors"]:
            print(f"- {error}")


def self_test_payload() -> dict[str, Any]:
    points = []
    sequence = 0
    for stroke_id in range(1, 4):
        for offset in range(8):
            sequence += 1
            points.append(
                {
                    "strokeId": stroke_id,
                    "sequence": sequence,
                    "phase": ("down" if offset == 0 else "up" if offset == 7 else "move"),
                    "pointerType": "pen",
                    "elapsedMs": sequence * 12,
                    "xNorm": min(1, 0.1 * stroke_id + offset * 0.01),
                    "yNorm": min(1, 0.15 * stroke_id + offset * 0.01),
                    "pressure": 0.2 + offset * 0.05,
                    "tiltX": 5 + offset,
                    "tiltY": 2 + offset,
                }
            )
    return {
        "schemaVersion": "1.0.0",
        "sessionId": "self-test",
        "participantId": "synthetic",
        "task": {
            "type": "copy_text",
            "promptId": "self-test-copy",
            "promptText": "Today, steady practice becomes tomorrow's confidence.",
        },
        "device": {},
        "canvas": {},
        "timing": {},
        "summary": {},
        "points": points,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查心迹AI在线笔迹轨迹JSON")
    parser.add_argument("path", nargs="?", type=Path, help="采集器导出的JSON文件")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出报告")
    parser.add_argument("--self-test", action="store_true", help="运行内置合成数据自测")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.self_test and args.path is None:
        print("请提供轨迹JSON路径，或使用 --self-test", file=sys.stderr)
        return 2
    try:
        payload = self_test_payload() if args.self_test else load_payload(args.path)
        report = analyse(payload)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"检查失败：{error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
