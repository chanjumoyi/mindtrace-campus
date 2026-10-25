"""Predeclared train/validation-only window study and real-data CUDA smoke."""

import argparse
import json
import os
import subprocess
import sys
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from mindtrace_ml.data import ML_ROOT, manifest, read_points, sha256
from mindtrace_ml.model import INPUT_CHANNELS
from mindtrace_ml.runtime import cpu_affinity
from mindtrace_ml.smoke import execute
from mindtrace_ml.trajectory import CHANNELS, Standardizer
from mindtrace_ml.windowing import VERSION, point_windows, prepare, preservation, time_windows


def read_development(record, reference):
    if record["split"] not in ("train", "val"):
        raise ValueError("test measurements are forbidden in window selection")
    previous = reference[record["source_id"]]
    for key in ("writer_id", "split"):
        if record[key] != previous[key]:
            raise ValueError("source participant/split changed")
    digest = sha256(record["path"])
    if digest != previous["sha256"]:
        raise ValueError("source differs from accepted inventory")
    return read_points(record["path"]), digest


def windows_for(record, candidate, plan):
    return list(
        time_windows(
            record,
            plan["duration_ms"],
            candidate["stride_ms"],
            candidate["short_minimum_ms"],
            plan["minimum_down_points"],
        )
    )


def coverage(source, windows, gap):
    t = source["relative_ms"]
    covered = np.zeros(len(t), dtype=bool)
    for window in windows:
        start, end = window["time_bounds_ms"]
        covered |= (t >= start) & (t < end)
    down = source["raw_points"][:, 4] == 1
    weight = np.r_[0, np.diff(t)]
    weight[(weight > gap) | ~down | source["stroke_boundary"]] = 0
    return (
        float((weight * covered).sum() / weight.sum())
        if weight.sum()
        else float(covered[down].mean())
    )


def select(candidates, plan):
    rule = plan["selection"]
    eligible = [
        c
        for c in candidates
        if c["position_p95"] is not None
        and c["pressure_p95"] is not None
        and c["position_p95"] <= rule["position_p95_max"]
        and c["pressure_p95"] <= rule["pressure_p95_max"]
        and c["coverage"] >= rule["minimum_down_time_coverage"]
    ]
    if not eligible:
        raise ValueError("no window candidate passes predeclared validation criteria")
    return min(eligible, key=lambda c: (c["points"], -c["stride_ms"], -c["short_minimum_ms"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-run", required=True, type=Path)
    parser.add_argument("--cpu-affinity", type=lambda value: int(value, 0))
    parser.add_argument("--freeze", action="store_true")
    args = parser.parse_args()
    affinity = cpu_affinity(args.cpu_affinity)
    input_run = args.input_run.resolve()
    if json.loads((input_run / "summary.json").read_text())["status"] != "passed":
        raise ValueError("accepted data run required")
    normalization = json.loads((input_run / "normalization.json").read_text())
    coordinates = normalization["coordinates"]
    if coordinates["fit_split"] != "train":
        raise ValueError("coordinate fit must be train-only")
    reference = {
        r["source_id"]: r for r in json.loads((input_run / "inventory.json").read_text())["records"]
    }
    plan = json.loads((ML_ROOT / "configs/window-study.json").read_text())
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    output = ML_ROOT / "experiments/window-study" / run_id
    output.mkdir(parents=True, exist_ok=False)
    # Persist the decision rule before opening any new trajectory measurements.
    (output / "study-plan.json").write_text(json.dumps(plan, indent=2))
    metadata = dict(
        run_id=run_id,
        cpu_affinity=affinity,
        input_run=str(input_run),
        code_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ML_ROOT, text=True
        ).strip(),
        plan_sha256=sha256(output / "study-plan.json"),
        test_measurement_policy="forbidden",
        implementation_sha256={
            str(p.relative_to(ML_ROOT)): sha256(p)
            for p in [Path(__file__), *sorted((ML_ROOT / "src/mindtrace_ml").glob("*.py"))]
        },
    )
    (output / "run.json").write_text(json.dumps(metadata, indent=2))
    records = [r for r in manifest() if r["split"] in ("train", "val")]
    candidates = []
    for rate in plan["rates_hz"]:
        for stride in plan["strides_ms"]:
            for short in plan["short_minimum_ms"]:
                candidates.append(
                    dict(
                        id=f"{rate or 'raw'}hz-stride{stride}-short{short}",
                        rate_hz=rate,
                        stride_ms=stride,
                        short_minimum_ms=short,
                        points=0,
                        windows=0,
                        writers=defaultdict(list),
                    )
                )
    audit = []
    for index, r in enumerate(record for record in records if record["split"] == "val"):
        points, digest = read_development(r, reference)
        source = prepare(points, coordinates, max_gap_ms=plan["maximum_interpolation_gap_ms"])
        variants = {
            rate: prepare(points, coordinates, rate, plan["maximum_interpolation_gap_ms"])
            for rate in plan["rates_hz"]
        }
        quality = {rate: preservation(source, variant) for rate, variant in variants.items()}
        for candidate in candidates:
            sampled = variants[candidate["rate_hz"]]
            chunks = windows_for(sampled, candidate, plan)
            candidate["points"] += sum(len(w["values"]) for w in chunks)
            candidate["windows"] += len(chunks)
            candidate["writers"][r["writer_id"]].append(
                dict(
                    **quality[candidate["rate_hz"]],
                    coverage=coverage(source, chunks, plan["maximum_interpolation_gap_ms"]),
                )
            )
        audit.append(
            dict(
                source_id=r["source_id"], sha256=digest, split=r["split"], writer_id=r["writer_id"]
            )
        )
        if index % 40 == 0:
            print(f"validation engineering audit {index + 1}/239", flush=True)
    for candidate in candidates:
        by_writer = candidate.pop("writers")
        candidate["validation_writers"] = len(by_writer)
        for key in ("position_p95", "pressure_p95", "coverage"):
            values = [
                np.mean([r[key] for r in rows])
                for rows in by_writer.values()
                if all(r[key] is not None for r in rows)
            ]
            if len(values) != len(by_writer):
                candidate[key] = None
            else:
                candidate[key] = float(min(values) if key == "coverage" else max(values))
    (output / "comparison.json").write_text(json.dumps(candidates, indent=2))
    selected = select(candidates, plan)
    print(f"selected engineering candidate: {selected['id']}", flush=True)
    # Refit channel statistics for the selected rate using every official train record.
    selected_training = {}
    for split, count in (
        ("train", plan["smoke"]["train_writers"]),
        ("val", plan["smoke"]["val_writers"]),
    ):
        participants = sorted({r["writer_id"] for r in records if r["split"] == split})[:count]
        selected_training[split] = {writer: None for writer in participants}
    cache = []

    def train_records():
        for index, r in enumerate(record for record in records if record["split"] == "train"):
            points, digest = read_development(r, reference)
            sampled = prepare(
                points, coordinates, selected["rate_hz"], plan["maximum_interpolation_gap_ms"]
            )
            audit.append(
                dict(
                    source_id=r["source_id"],
                    sha256=digest,
                    split=r["split"],
                    writer_id=r["writer_id"],
                )
            )
            if (
                r["writer_id"] in selected_training["train"]
                and selected_training["train"][r["writer_id"]] is None
            ):
                selected_training["train"][r["writer_id"]] = r["source_id"]
                cache.append(("train", r, points, sampled))
            if index % 200 == 0:
                print(f"train-only channel fit {index + 1}/1911", flush=True)
            yield "train", sampled

    scaler = Standardizer().fit(train_records())
    (output / "normalization.json").write_text(
        json.dumps(
            dict(
                coordinates=coordinates,
                mean=scaler.mean.tolist(),
                scale=scaler.scale.tolist(),
                fit_split="train",
                channels=CHANNELS,
            ),
            indent=2,
        )
    )
    for r in records:
        if (
            r["split"] == "val"
            and r["writer_id"] in selected_training["val"]
            and selected_training["val"][r["writer_id"]] is None
        ):
            points, _ = read_development(r, reference)
            selected_training["val"][r["writer_id"]] = r["source_id"]
            cache.append(
                (
                    "val",
                    r,
                    points,
                    prepare(
                        points,
                        coordinates,
                        selected["rate_hz"],
                        plan["maximum_interpolation_gap_ms"],
                    ),
                )
            )
    datasets = {mode: {split: [] for split in ("train", "val")} for mode in ("debug256", "formal")}
    for split, _record, points, sampled in cache:
        raw = prepare(points, coordinates, max_gap_ms=plan["maximum_interpolation_gap_ms"])
        for mode, chunks in (
            ("debug256", list(point_windows(raw))),
            ("formal", windows_for(sampled, selected, plan)),
        ):
            if not chunks:
                continue
            indices = np.unique(
                np.linspace(
                    0,
                    len(chunks) - 1,
                    min(plan["smoke"]["windows_per_record"], len(chunks)),
                    dtype=int,
                )
            )
            for index in indices:
                chunk = chunks[index]
                chunk["values"] = scaler.apply(chunk["values"], chunk["feature_mask"])
                datasets[mode][split].append(chunk)
    smoke = {}
    for mode, data in datasets.items():
        print(f"CUDA real-data smoke: {mode}", flush=True)
        smoke[mode] = execute(
            data["train"], data["val"], output / mode, plan["smoke"], plan["seed"]
        )
    unchanged = all(
        sha256(next(r["path"] for r in records if r["source_id"] == entry["source_id"]))
        == entry["sha256"]
        for entry in audit
    )
    if not unchanged:
        raise RuntimeError("source changed during study")
    (output / "source-audit.json").write_text(json.dumps(audit, indent=2))
    frozen = dict(
        version="ouhd-input-v2",
        preprocessing_version=VERSION,
        observations=list(CHANNELS),
        model_input=INPUT_CHANNELS,
        target_channels=list(CHANNELS[:4]),
        duration_ms=plan["duration_ms"],
        rate_hz=selected["rate_hz"],
        stride_ms=selected["stride_ms"],
        short_minimum_ms=selected["short_minimum_ms"],
        short_policy="retain then batch-pad; never truncate",
        interpolation=plan["interpolation"] if selected["rate_hz"] else "none",
        maximum_interpolation_gap_ms=plan["maximum_interpolation_gap_ms"],
        minimum_down_points=plan["minimum_down_points"],
        normalization="train-only coordinates; selected-rate train-only channel moments; pen_state unchanged",
        selection_source="all official validation records, writer aggregated engineering criteria",
        debug_256_formal_allowed=False,
        test_used_for_selection=False,
    )
    result = dict(
        **metadata,
        status="passed",
        selected=selected,
        smoke=smoke,
        raw_hashes_unchanged=unchanged,
        training_records=sum(r["split"] == "train" for r in records),
        validation_records=sum(r["split"] == "val" for r in records),
        test_measurements_opened=sum(r["split"] == "test" for r in audit),
    )
    (output / "summary.json").write_text(json.dumps(result, indent=2))
    (output / "preprocessing-frozen.json").write_text(json.dumps(frozen, indent=2))
    if args.freeze:
        target = ML_ROOT / "configs/preprocessing-frozen.json"
        if target.exists():
            raise ValueError(
                "frozen protocol exists; version changes require an explicit new study"
            )
        target.write_text(json.dumps(frozen, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                output=str(output),
                selected=selected,
                smoke=smoke,
                status="passed",
                test_measurements_opened=0,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
