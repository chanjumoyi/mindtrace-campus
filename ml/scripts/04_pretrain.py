"""OUHD-L formal pretraining. Private outputs only; test opens after encoder freeze."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import torch

from mindtrace_ml.checkpoint import fingerprint
from mindtrace_ml.data import ML_ROOT, manifest, read_points, sha256
from mindtrace_ml.pretraining import (
    complete_evaluation,
    evaluate,
    resume_completed,
    train,
    write_json,
)
from mindtrace_ml.runtime import cpu_affinity
from mindtrace_ml.trajectory import Standardizer
from mindtrace_ml.windowing import VERSION, prepare, time_windows


def load_json(path):
    return json.loads(path.read_text())


def build(records, reference, frozen, normalization, output, split):
    scaler = Standardizer()
    scaler.mean = np.array(normalization["mean"])
    scaler.scale = np.array(normalization["scale"])
    samples, index = [], []
    offsets = [0]
    spans, lefts, rights, alphas = [], [], [], []
    for number, record in enumerate(r for r in records if r["split"] == split):
        previous = reference[record["source_id"]]
        if (
            any(record[k] != previous[k] for k in ("writer_id", "split"))
            or sha256(record["path"]) != previous["sha256"]
        ):
            raise ValueError("source hash or participant/split changed")
        sampled = prepare(
            read_points(record["path"]),
            normalization["coordinates"],
            frozen["rate_hz"],
            frozen["maximum_interpolation_gap_ms"],
            frozen["pressure"]["range"],
        )
        count = 0
        for window in time_windows(
            sampled,
            frozen["duration_ms"],
            frozen["stride_ms"],
            frozen["short_minimum_ms"],
            frozen["minimum_down_points"],
            frozen["maximum_interpolation_gap_ms"],
        ):
            samples.append(
                dict(
                    values=scaler.apply(window["values"], window["feature_mask"]).astype(
                        np.float32
                    ),
                    feature_mask=window["feature_mask"],
                    stroke_boundary=window["stroke_boundary"],
                )
            )
            offsets.append(offsets[-1] + len(window["values"]))
            spans.append(window["source_spans"])
            lefts.append(window["source_left_spans"])
            rights.append(window["source_right_spans"])
            alphas.append(window["source_alpha"])
            index.append(
                dict(
                    source_id=record["source_id"],
                    writer_id=record["writer_id"],
                    split=split,
                    sha256=previous["sha256"],
                    time_bounds_ms=list(window["time_bounds_ms"]),
                )
            )
            count += 1
        if not count:
            raise ValueError("official record produced no eligible windows")
        if sha256(record["path"]) != previous["sha256"]:
            raise ValueError("source changed during processing")
        if number % 200 == 0:
            print(f"prepare {split}: {number + 1} records, {len(samples)} windows", flush=True)
    if not samples:
        raise ValueError("empty split")
    np.savez(
        output / f"{split}.npz",
        offsets=np.array(offsets),
        values=np.concatenate([s["values"] for s in samples]),
        feature_mask=np.concatenate([s["feature_mask"] for s in samples]),
        stroke_boundary=np.concatenate([s["stroke_boundary"] for s in samples]),
        source_spans=np.concatenate(spans),
        source_left_spans=np.concatenate(lefts),
        source_right_spans=np.concatenate(rights),
        source_alpha=np.concatenate(alphas),
    )
    write_json(output / f"{split}-index.json", index)
    return samples


def cached(path):
    with np.load(path, allow_pickle=False) as data:
        offsets = data["offsets"]
        arrays = {k: data[k] for k in ("values", "feature_mask", "stroke_boundary")}
    return [
        {k: v[a:b] for k, v in arrays.items()}
        for a, b in zip(offsets[:-1], offsets[1:], strict=True)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study-run", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--cpu-affinity", type=lambda v: int(v, 0))
    args = parser.parse_args()
    affinity = cpu_affinity(args.cpu_affinity)
    study = args.study_run.resolve()
    summary = load_json(study / "summary.json")
    frozen = load_json(ML_ROOT / "configs/preprocessing-frozen.json")
    normalization = load_json(study / "normalization.json")
    if (
        summary["status"] != "passed"
        or summary["test_measurements_opened"] != 0
        or load_json(study / "preprocessing-frozen.json") != frozen
        or frozen["preprocessing_version"] != VERSION
        or normalization["fit_split"] != "train"
        or normalization["coordinates"]["fit_split"] != "train"
        or normalization["source_metadata"] != frozen["source_metadata"]
        or normalization["pressure"] != frozen["pressure"]
    ):
        raise ValueError("passed, compatible train-only frozen study required")
    accepted = Path(summary["input_run"])
    if sha256(accepted / "inventory.json") != summary["inventory_sha256"]:
        raise ValueError("accepted inventory changed")
    reference = {r["source_id"]: r for r in load_json(accepted / "inventory.json")["records"]}
    records = manifest()
    if {r["source_id"] for r in records} != set(reference):
        raise ValueError("inventory membership changed")
    config = load_json(ML_ROOT / "configs/pretraining.json")
    output = args.output or ML_ROOT / "experiments/pretraining" / datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%SZ")
    output = output.resolve()
    contract = dict(
        frozen=frozen,
        normalization=normalization,
        study_summary_sha256=sha256(study / "summary.json"),
        inventory_sha256=sha256(accepted / "inventory.json"),
        manifest_sha256=fingerprint(
            [{k: r[k] for k in ("source_id", "writer_id", "split")} for r in records]
        ),
        implementation_sha256={
            str(p.relative_to(ML_ROOT)): sha256(p)
            for p in [Path(__file__), *sorted((ML_ROOT / "src/mindtrace_ml").glob("*.py"))]
        },
    )
    if args.resume:
        previous = load_json(output / "input-contract.json")
        if previous["source"] != contract:
            raise ValueError("resume source/code incompatible")
        for name, digest in previous["cache_sha256"].items():
            if sha256(output / name) != digest:
                raise ValueError("resume cache changed")
        if resume_completed(output, config, previous):
            print(
                "formal run already evaluated; frozen files preserved, completion metadata checked",
                flush=True,
            )
            return
        if not torch.cuda.is_available():
            raise RuntimeError("formal run requires CUDA")
        data = {s: cached(output / f"{s}.npz") for s in ("train", "val")}
        input_contract = previous
    else:
        if not torch.cuda.is_available():
            raise RuntimeError("formal run requires CUDA")
        output.mkdir(parents=True, exist_ok=False)
        print(f"private formal run: {output}", flush=True)
        write_json(
            output / "run.json",
            dict(
                cpu_affinity=affinity,
                gpu=torch.cuda.get_device_name(),
                code_commit=subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ML_ROOT, text=True
                ).strip(),
            ),
        )
        write_json(output / "pretraining.json", config)
        write_json(output / "normalization.json", normalization)
        write_json(output / "preprocessing-frozen.json", frozen)
        data = {
            s: build(records, reference, frozen, normalization, output, s) for s in ("train", "val")
        }
        input_contract = dict(
            source=contract,
            cache_sha256={
                f"{s}{suffix}": sha256(output / f"{s}{suffix}")
                for s in ("train", "val")
                for suffix in (".npz", "-index.json")
            },
        )
        write_json(output / "input-contract.json", input_contract)
    model, history = train(
        data["train"], data["val"], output, config, input_contract, resume=args.resume
    )
    del data
    # Durable claim before touching test: interrupted evaluation cannot silently be repeated.
    claim = output / "test-started.json"
    if claim.exists():
        raise RuntimeError(
            "test evaluation previously started; review interruption before a new evaluation"
        )
    encoder_hash = sha256(output / "encoder.pt")
    write_json(
        claim, dict(encoder_sha256=encoder_hash, frozen_sha256=sha256(output / "frozen.json"))
    )
    test = build(records, reference, frozen, normalization, output, "test")
    metrics = evaluate(model, test, config, "cuda", config["test_seed"])
    if sha256(output / "encoder.pt") != encoder_hash:
        raise RuntimeError("encoder changed during test")
    write_json(
        output / "test-metrics.json",
        dict(
            metrics=metrics,
            encoder_sha256=encoder_hash,
            windows=len(test),
            units="train-standardized channels",
            evaluation_count=1,
        ),
    )
    complete_evaluation(output, history)
    print(json.dumps(dict(output=str(output), test=metrics), indent=2), flush=True)


if __name__ == "__main__":
    main()
