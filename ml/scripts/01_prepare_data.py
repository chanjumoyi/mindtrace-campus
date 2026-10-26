"""Read-only full audit and private derivative generation. Run from any cwd."""

import argparse
import json
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from mindtrace_ml.contracts import run_metadata, validate_features, validate_saved_window
from mindtrace_ml.data import ML_ROOT, config, manifest, read_points, sha256
from mindtrace_ml.features import extract, plot
from mindtrace_ml.runtime import cpu_affinity
from mindtrace_ml.trajectory import (
    Standardizer,
    fit_coordinates,
    pressure_parameters,
    repair,
    transform,
    windows,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-arrays", action="store_true")
    parser.add_argument("--window-ms", type=int, default=2000)
    parser.add_argument("--stride-ms", type=int, default=2000)
    parser.add_argument("--cpu-affinity", type=lambda value: int(value, 0), default=None)
    parser.add_argument(
        "--sample-arrays", action="store_true", help="save one window per official split"
    )
    args = parser.parse_args()
    affinity = cpu_affinity(args.cpu_affinity)
    pressure = pressure_parameters()
    metadata = run_metadata(args.window_ms, args.stride_ms, pressure)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8]
    output = ML_ROOT / "data/processed/ouhd_l-v1" / run_id
    output.mkdir(parents=True, exist_ok=False)
    print(f"private output: {output}", flush=True)
    records = manifest()
    print(f"manifest validated: {len(records)} records; hashing originals", flush=True)
    before = {}
    for i, r in enumerate(records):
        before[r["source_id"]] = sha256(r["path"])
        if i % 400 == 0:
            print(f"hashed {i}/{len(records)}", flush=True)
    training_rejected = set()

    def training():
        for i, r in enumerate(records):
            if r["split"] == "train":
                try:
                    points, _, _ = repair(read_points(r["path"]))
                    if i % 200 == 0:
                        print(f"train fit {i}/{len(records)}", flush=True)
                    yield "train", points
                except (ValueError, OSError):
                    training_rejected.add(r["source_id"])

    coords = fit_coordinates(training())
    print("training coordinate map fitted", flush=True)
    scaler = Standardizer().fit(
        ("train", transform(p, coords, pressure["range"])) for _, p in training()
    )
    (output / "normalization.json").write_text(
        json.dumps(
            dict(
                **metadata,
                version=metadata["trajectory_version"],
                normalization_channels=metadata["channels"][:4],
                coordinates=coords,
                mean=scaler.mean.tolist(),
                scale=scaler.scale.tolist(),
            ),
            indent=2,
        )
    )
    counts, points, duplicate_files, merged, transitions = Counter(), 0, 0, 0, 0
    writers = {s: set() for s in ("train", "val", "test")}
    private, failures, sampled = [], [], 0
    array_samples = set()
    started = time.perf_counter()
    for index, r in enumerate(records):
        try:
            raw = read_points(r["path"])
            points += len(raw)
            duplicate = bool((np.diff(raw[:, 3]) == 0).any())
            duplicate_files += duplicate
            trajectory = transform(raw, coords, pressure["range"])
            features = extract(trajectory)
            validate_features(features)
            merged += trajectory["quality"]["merged_points"]
            transitions += trajectory["quality"]["zero_dt_transitions"]
            count = 0
            for count, window in enumerate(windows(trajectory, args.window_ms, args.stride_ms), 1):
                if args.write_arrays or (args.sample_arrays and r["split"] not in array_samples):
                    folder = output / r["split"] / str(index)
                    folder.mkdir(parents=True, exist_ok=True)
                    window["values"] = scaler.apply(window["values"], window["feature_mask"])
                    np.savez_compressed(
                        folder / f"{count}.npz",
                        **{
                            key: json.dumps(value) if isinstance(value, dict) else value
                            for key, value in window.items()
                        },
                        dataset="ouhd_l",
                        schema_version=metadata["trajectory_version"],
                        features_version=metadata["features_version"],
                        window_ms=metadata["window_ms"],
                        stride_ms=metadata["stride_ms"],
                        writer_id=r["writer_id"],
                        split=r["split"],
                        source_id=r["source_id"],
                        source_sha256=before[r["source_id"]],
                    )
                    with np.load(folder / f"{count}.npz", allow_pickle=False) as saved:
                        validate_saved_window(saved, metadata)
                    array_samples.add(r["split"])
            if duplicate and sampled < 6:
                plot(trajectory, output / f"duplicate-sample-{sampled}.png")
                sampled += 1
            private.append(
                dict(
                    source_id=r["source_id"],
                    writer_id=r["writer_id"],
                    split=r["split"],
                    sha256=before[r["source_id"]],
                    windows=count,
                    quality=trajectory["quality"],
                    features=features,
                )
            )
            counts[r["split"]] += 1
            writers[r["split"]].add(r["writer_id"])
        except (ValueError, OSError) as exc:
            failures.append(dict(source_id=r["source_id"], reason=str(exc)))
        if index % 200 == 0:
            print(f"processed {index}/{len(records)}", flush=True)
    unchanged = all(sha256(r["path"]) == before[r["source_id"]] for r in records)
    summary = dict(
        **metadata,
        run_id=run_id,
        status="passed" if unchanged and not failures else "needs_review",
        cpu_affinity=affinity,
        records=len(records),
        points=points,
        splits=dict(counts),
        writers={k: len(v) for k, v in writers.items()},
        duplicate_files=duplicate_files,
        merged_points=merged,
        zero_dt_transitions=transitions,
        quarantined=len(failures),
        training_quarantined=len(training_rejected),
        raw_hashes_unchanged=unchanged,
        seconds=round(time.perf_counter() - started, 2),
        normalization="train only; coordinate extent, not physical device calibration",
        permission=config()["ouhd_l"]["permission"],
        formal_windows_frozen=False,
    )
    (output / "inventory.json").write_text(
        json.dumps(dict(records=private, quarantine=failures), indent=2)
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if not unchanged or failures:
        raise SystemExit("source mutation or quarantine: review local inventory")


if __name__ == "__main__":
    main()
