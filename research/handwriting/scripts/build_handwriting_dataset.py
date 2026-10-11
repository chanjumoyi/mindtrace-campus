#!/usr/bin/env python3
"""Build a flat, auditable handwriting feature table from the private manifest."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_feature_extractor():
    """Import the extractor shared with the API service.

    The feature definition must stay in one place, so this script reuses
    ``backend/app/services/handwriting/features.py`` instead of keeping a second
    copy that can drift.
    """
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from backend.app.services.handwriting.features import extract, load_points

    return extract, load_points


def pick(data: dict[str, Any], *path: str) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def as_bool(value: Any) -> bool:
    return value is True


def flatten(row: dict[str, str], features: dict[str, Any]) -> dict[str, Any]:
    pointer_types = pick(features, "device", "pointerTypes") or []
    pressure_count = pick(features, "pressure", "count") or 0
    pressure_min = pick(features, "pressure", "min")
    pressure_max = pick(features, "pressure", "max")
    pressure_range = (
        pressure_max - pressure_min
        if isinstance(pressure_min, int | float) and isinstance(pressure_max, int | float)
        else 0
    )
    points = pick(features, "counts", "points") or 0
    strokes = pick(features, "counts", "strokes") or 0
    collection_usable = (
        pointer_types == ["pen"]
        and points >= 500
        and strokes >= 20
        and pressure_count >= 100
        and pressure_range >= 0.01
    )
    reasons: list[str] = []
    if pointer_types != ["pen"]:
        reasons.append("contains_non_pen_input")
    if points < 500:
        reasons.append("too_few_points")
    if strokes < 20:
        reasons.append("too_few_strokes")
    if pressure_count < 100 or pressure_range < 0.01:
        reasons.append("pressure_unusable")

    bbox = pick(features, "geometry", "normalizedBoundingBox") or {}
    return {
        "sample_id": row["sample_id"],
        "participant_id": row["participant_id"],
        "date": row["date"],
        "task_type": row["task_type"],
        "context_code": row["context_code"],
        "stress_level": row["stress_level"],
        "mood_level": row["mood_level"],
        "sleep_quality": row["sleep_quality"],
        "collection_usable": collection_usable,
        "personal_baseline_usable": collection_usable,
        "supervised_training_usable": False,
        "exclusion_reason": ";".join(reasons),
        "supervised_exclusion_reason": "single_participant_single_day_no_independent_ground_truth",
        "point_count": points,
        "stroke_count": strokes,
        "duration_ms": pick(features, "timing", "taskDurationMs"),
        "zero_interval_count": pick(features, "counts", "zeroIntervalPoints"),
        "long_pause_count": pick(features, "counts", "longPauseCount"),
        "pen_up_ratio": pick(features, "timing", "penUpRatio"),
        "within_interval_median_ms": pick(features, "timing", "withinStrokeIntervalMs", "median"),
        "within_interval_p95_ms": pick(features, "timing", "withinStrokeIntervalMs", "p95"),
        "between_pause_median_ms": pick(features, "timing", "betweenStrokePauseMs", "median"),
        "between_pause_p95_ms": pick(features, "timing", "betweenStrokePauseMs", "p95"),
        "pressure_mean": pick(features, "pressure", "mean"),
        "pressure_std": pick(features, "pressure", "std"),
        "pressure_p10": pick(features, "pressure", "p10"),
        "pressure_p90": pick(features, "pressure", "p90"),
        "tilt_x_mean": pick(features, "tiltX", "mean"),
        "tilt_x_std": pick(features, "tiltX", "std"),
        "tilt_y_mean": pick(features, "tiltY", "mean"),
        "tilt_y_std": pick(features, "tiltY", "std"),
        "path_length_px": pick(features, "kinematics", "totalPathLengthPx"),
        "stroke_length_mean_px": pick(features, "kinematics", "strokeLengthPx", "mean"),
        "stroke_length_std_px": pick(features, "kinematics", "strokeLengthPx", "std"),
        "speed_median_px_s": pick(features, "kinematics", "speedPxPerSecond", "median"),
        "speed_mean_px_s": pick(features, "kinematics", "speedPxPerSecond", "mean"),
        "speed_std_px_s": pick(features, "kinematics", "speedPxPerSecond", "std"),
        "speed_p90_px_s": pick(features, "kinematics", "speedPxPerSecond", "p90"),
        "bbox_width_norm": bbox.get("width"),
        "bbox_height_norm": bbox.get("height"),
        "bbox_area_norm": bbox.get("area"),
        "supports_pressure": as_bool(pick(features, "device", "supportsPressure")),
        "supports_tilt": as_bool(pick(features, "device", "supportsTilt")),
        "feature_warnings": ";".join(features.get("warnings", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="批量生成心迹AI笔迹特征数据集")
    parser.add_argument("--private-root", type=Path, default=Path("research/handwriting/private"))
    args = parser.parse_args()
    root = args.private_root.resolve()
    manifest = root / "manifests" / "sessions.csv"
    if not manifest.is_file():
        parser.error(f"未找到私有数据清单：{manifest}；私有数据不进仓库，请先运行导入脚本")
    extract, load_points = load_feature_extractor()
    output_dir = root / "features"
    output_dir.mkdir(parents=True, exist_ok=True)

    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        parser.error(f"清单中没有任何样本：{manifest}")

    flat_rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for row in rows:
        sample_id = row.get("sample_id") or "<unknown>"
        raw_json = row.get("raw_json")
        if not raw_json:
            skipped.append(f"{sample_id}: 清单缺少 raw_json 字段")
            continue
        try:
            payload, points = load_points(root / raw_json)
            features = extract(payload, points)
        except (OSError, ValueError) as error:
            # One unreadable trace must not discard the samples already extracted.
            skipped.append(f"{sample_id}: {type(error).__name__}: {error}")
            continue
        feature_path = output_dir / f"{sample_id}.features.json"
        feature_path.write_text(
            json.dumps(features, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        flat_rows.append(flatten(row, features))

    if not flat_rows:
        parser.error(
            f"没有任何样本成功提取特征（跳过 {len(skipped)} 条）：{'; '.join(skipped[:3])}"
        )
    if skipped:
        print(f"已跳过 {len(skipped)} 条无法读取的样本：{'; '.join(skipped[:3])}")

    table_path = output_dir / "modeling_dataset_v0.1.csv"
    with table_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    participants = Counter(row["participant_id"] for row in flat_rows)
    tasks = Counter(row["task_type"] for row in flat_rows)
    usable = sum(bool(row["collection_usable"]) for row in flat_rows)
    card = f"""# 笔迹数据集卡 v0.1

- 样本数：{len(flat_rows)}
- 采集可用：{usable}
- 参与者：{len(participants)}（{dict(participants)}）
- 任务分布：{dict(tasks)}
- 采集日期数：{len(set(row["date"] for row in flat_rows))}
- 设备：华为平板 + Huawei Pencil；浏览器 Pointer Events

## 当前允许用途

- 验证压感、倾角、轨迹和图片采集链路。
- 建立同一参与者的个人笔迹基线，比较重复采集的稳定性。
- 开发特征提取、可视化、异常检测和接口联调。

## 当前禁止宣称

- 不可据此训练或证明通用的焦虑、抑郁、人格或心理风险识别模型。
- 不可将书籍中的笔迹解释直接作为医学或心理标签。
- 不可随机拆分同一参与者的重复样本后宣称泛化准确率。

## 进入监督学习前的最低补充

- 增加不同参与者，并按参与者划分训练、验证和测试集。
- 统一采集任务、姿势、设备和时间窗口，同时记录知情同意。
- 使用规范自评量表或专业人员审核结果作为独立标签；笔迹书仅用于特征假设。
"""
    (output_dir / "dataset_card_v0.1.md").write_text(card, encoding="utf-8")
    print(
        json.dumps(
            {
                "samples": len(flat_rows),
                "collectionUsable": usable,
                "tasks": dict(tasks),
                "table": str(table_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
