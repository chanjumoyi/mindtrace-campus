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

from mindtrace_ml.checkpoint import environment, fingerprint
from mindtrace_ml.contracts import run_metadata
from mindtrace_ml.data import ML_ROOT, manifest, read_points, sha256
from mindtrace_ml.model import INPUT_CHANNELS
from mindtrace_ml.runtime import cpu_affinity
from mindtrace_ml.smoke import execute
from mindtrace_ml.trajectory import CHANNELS, Standardizer, pressure_parameters
from mindtrace_ml.windowing import VERSION, point_windows, prepare, preservation, time_windows

# These named policies have one implemented variant. Reject edits instead of
# recording an unsupported policy as if it had actually run.
FIXED_POLICIES = {
    "aggregation": "worst writer mean of record p95 errors and record coverage",
    "eligible_order": ["fewest points", "largest stride", "longest minimum short window"],
    "fallback": "fail without freezing if no candidate passes",
    "coverage_policy": "exact union overlap with valid continuous pen-down time edges; no gap or pen-up weighting",
    "interpolation": "linear within continuous pen-down segment only; pen-up endpoints only",
}


def validate_plan(plan):
    for key, supported in FIXED_POLICIES.items():
        actual = (
            plan["selection"].get(key)
            if key in ("aggregation", "eligible_order", "fallback")
            else plan.get(key)
        )
        if actual != supported:
            raise ValueError(f"unsupported study policy: {key}")
    for key in ("train_writers", "val_writers", "records_per_writer", "windows_per_record"):
        value = plan["smoke"].get(key)
        if type(value) is not int or value <= 0:
            raise ValueError(f"positive integer required: smoke.{key}")


def validate_manifest(records, reference):
    ids = [r["source_id"] for r in records]
    if len(ids) != len(set(ids)) or set(ids) != set(reference):
        raise ValueError("development manifest differs from accepted inventory source set")
    for record in records:
        previous = reference[record["source_id"]]
        if record["split"] not in ("train", "val") or any(
            record[k] != previous[k] for k in ("split", "writer_id")
        ):
            raise ValueError(
                "development manifest participant/split differs from accepted inventory"
            )


def smoke_sources(records, plan):
    """Sorted writers, manifest-order records; no trajectory access or test selection."""
    selected = set()
    count = plan["smoke"]["records_per_writer"]
    for split, key in (("train", "train_writers"), ("val", "val_writers")):
        grouped = defaultdict(list)
        for record in records:
            if record["split"] == split:
                grouped[record["writer_id"]].append(record["source_id"])
        writers = sorted(grouped)[: plan["smoke"][key]]
        if len(writers) != plan["smoke"][key] or any(len(grouped[w]) < count for w in writers):
            raise ValueError("insufficient writers/records for predeclared smoke plan")
        for writer in writers:
            selected.update(grouped[writer][:count])
    return selected


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
            plan["maximum_interpolation_gap_ms"],
        )
    )


def coverage(source, windows, gap):
    t = source["relative_ms"]
    down = source["raw_points"][:, 4] == 1
    edges = [
        (a, b)
        for i, (a, b) in enumerate(zip(t[:-1], t[1:], strict=False))
        if down[i] and down[i + 1] and 0 < b - a <= gap and not source["stroke_boundary"][i + 1]
    ]
    intervals = sorted(w["time_bounds_ms"] for w in windows)
    union = []
    for a, b in intervals:
        if union and a <= union[-1][1]:
            union[-1][1] = max(b, union[-1][1])
        else:
            union.append([a, b])
    total = sum(b - a for a, b in edges)
    if total:
        return float(sum(max(0, min(b, y) - max(a, x)) for a, b in edges for x, y in union) / total)
    covered = np.zeros(len(t), dtype=bool)
    for a, b in union:
        covered |= (t >= a) & (t < b)
    return float(covered[down].mean()) if down.any() else 0.0


def select(candidates, plan):
    rule = plan["selection"]
    eligible = [
        c
        for c in candidates
        if c["position_p95"] is not None
        and c["pressure_p95"] is not None
        and c["position_p95"] <= rule["position_p95_max"]
        and c["pressure_p95"] <= rule["pressure_p95_max"]
        and c.get("pressure_comparable_fraction", 1.0)
        >= rule.get("minimum_pressure_comparable_fraction", 1.0)
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
    parser.add_argument("--replace-frozen-version")
    args = parser.parse_args()
    affinity = cpu_affinity(args.cpu_affinity)
    input_run = args.input_run.resolve()
    accepted = json.loads((input_run / "summary.json").read_text())
    if accepted["status"] != "passed":
        raise ValueError("accepted data run required")
    normalization = json.loads((input_run / "normalization.json").read_text())
    pressure = pressure_parameters()
    required = run_metadata(2000, 2000, pressure)
    if any(normalization.get(k) != v or accepted.get(k) != v for k, v in required.items()):
        raise ValueError("accepted input preprocessing/pressure metadata incompatible")
    coordinates = normalization["coordinates"]
    if coordinates["fit_split"] != "train":
        raise ValueError("coordinate fit must be train-only")
    reference = {
        r["source_id"]: r
        for r in json.loads((input_run / "inventory.json").read_text())["records"]
        if r["split"] in ("train", "val")
    }
    plan = json.loads((ML_ROOT / "configs/window-study.json").read_text())
    validate_plan(plan)
    target = ML_ROOT / "configs/preprocessing-frozen.json"
    previous = json.loads(target.read_text()) if target.exists() else None
    if (
        args.freeze
        and previous
        and (
            args.replace_frozen_version != previous["version"]
            or previous["version"] == "ouhd-input-v3"
        )
    ):
        raise ValueError("explicit old frozen version required for a new versioned study")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    output = ML_ROOT / "experiments/window-study" / run_id
    output.mkdir(parents=True, exist_ok=False)
    # Persist the decision rule before opening any new trajectory measurements.
    (output / "study-plan.json").write_text(json.dumps(plan, indent=2))
    if previous:
        (output / "previous-preprocessing-frozen.json").write_text(json.dumps(previous, indent=2))
    metadata = dict(
        environment=environment(),
        pressure=pressure,
        preprocessing_version=VERSION,
        accepted_metadata=required,
        inventory_sha256=sha256(input_run / "inventory.json"),
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
    validate_manifest(records, reference)
    selected_sources = smoke_sources(records, plan)
    metadata["development_manifest_sha256"] = fingerprint(
        [{k: r[k] for k in ("source_id", "writer_id", "split")} for r in records]
    )
    (output / "run.json").write_text(json.dumps(metadata, indent=2))

    def prepare_input(points, coordinates, rate_hz=None, max_gap_ms=200):
        return prepare(points, coordinates, rate_hz, max_gap_ms, pressure["range"])

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
        source = prepare_input(points, coordinates, max_gap_ms=plan["maximum_interpolation_gap_ms"])
        variants = {
            rate: prepare_input(points, coordinates, rate, plan["maximum_interpolation_gap_ms"])
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
        for key in ("position_p95", "pressure_p95", "coverage", "pressure_comparable_fraction"):
            values = [
                np.mean([r[key] for r in rows])
                for rows in by_writer.values()
                if all(r[key] is not None for r in rows)
            ]
            if len(values) != len(by_writer):
                candidate[key] = None
            else:
                candidate[key] = float(
                    min(values)
                    if key in ("coverage", "pressure_comparable_fraction")
                    else max(values)
                )
    (output / "comparison.json").write_text(json.dumps(candidates, indent=2))
    selected = select(candidates, plan)
    print(f"selected engineering candidate: {selected['id']}", flush=True)
    # Refit channel statistics for the selected rate using every official train record.
    cache = []

    def train_records():
        for index, r in enumerate(record for record in records if record["split"] == "train"):
            points, digest = read_development(r, reference)
            sampled = prepare_input(
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
            if r["source_id"] in selected_sources:
                cache.append(("train", r, points, sampled))
            if index % 200 == 0:
                print(f"train-only channel fit {index + 1}/1911", flush=True)
            yield "train", sampled

    scaler = Standardizer().fit(train_records())
    (output / "normalization.json").write_text(
        json.dumps(
            dict(
                preprocessing_version=VERSION,
                pressure=pressure,
                source_metadata=required,
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
        if r["split"] == "val" and r["source_id"] in selected_sources:
            points, _ = read_development(r, reference)
            cache.append(
                (
                    "val",
                    r,
                    points,
                    prepare_input(
                        points,
                        coordinates,
                        selected["rate_hz"],
                        plan["maximum_interpolation_gap_ms"],
                    ),
                )
            )
    datasets = {mode: {split: [] for split in ("train", "val")} for mode in ("debug256", "formal")}
    window_index = []
    for split, _record, points, sampled in cache:
        raw = prepare_input(points, coordinates, max_gap_ms=plan["maximum_interpolation_gap_ms"])
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
                chunk["provenance"] = dict(
                    source_id=_record["source_id"],
                    writer_id=_record["writer_id"],
                    split=split,
                    source_sha256=reference[_record["source_id"]]["sha256"],
                    time_bounds_ms=list(chunk["time_bounds_ms"]),
                    mode=mode,
                    source_spans=chunk["source_spans"].tolist(),
                    source_left_spans=chunk["source_left_spans"].tolist(),
                    source_right_spans=chunk["source_right_spans"].tolist(),
                    source_alpha=chunk["source_alpha"].tolist(),
                )
                window_index.append(chunk["provenance"])
                chunk["values"] = scaler.apply(chunk["values"], chunk["feature_mask"])
                datasets[mode][split].append(chunk)
    (output / "window-index.json").write_text(json.dumps(window_index, indent=2))
    smoke = {}
    for mode, data in datasets.items():
        print(f"CUDA real-data smoke: {mode}", flush=True)
        smoke[mode] = execute(
            data["train"],
            data["val"],
            output / mode,
            plan["smoke"],
            plan["seed"],
            input_contract=dict(
                run=metadata,
                mode=mode,
                selected=selected,
                normalization_sha256=sha256(output / "normalization.json"),
                window_index_sha256=sha256(output / "window-index.json"),
            ),
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
        version="ouhd-input-v3",
        source_metadata=required,
        pressure=pressure,
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
