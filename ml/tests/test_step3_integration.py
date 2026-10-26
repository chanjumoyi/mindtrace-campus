"""Regressions for step-three integration; synthetic measurements only."""

import copy
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import torch
from mindtrace_ml.checkpoint import load_checked, sample_fingerprint
from mindtrace_ml.model import collate, masked_huber
from mindtrace_ml.smoke import execute
from mindtrace_ml.trajectory import pad
from mindtrace_ml.windowing import point_windows, prepare, preservation


def sample():
    t = np.arange(0, 65, 2)
    p = np.column_stack([t, t / 2, 100 + t, t, np.ones(len(t))])
    return prepare(p, dict(origin=[0, 0], scale=[100, 100]), pressure_range=[100, 200])


class IntegrationTests(unittest.TestCase):
    def test_pressure_contract_partial_missing_and_debug_metadata(self):
        source = sample()
        sampled = prepare(
            source["raw_points"],
            dict(origin=[0, 0], scale=[100, 100]),
            250,
            pressure_range=[100, 200],
        )
        metrics = preservation(source, sampled)
        self.assertLess(metrics["pressure_p95"], 1e-12)
        sampled["feature_mask"][3, 3] = False
        metrics = preservation(source, sampled)
        self.assertGreater(metrics["pressure_comparable_fraction"], 0)
        self.assertLess(metrics["pressure_comparable_fraction"], 1)
        self.assertLess(metrics["pressure_p95"], 1e-12)
        debug = next(point_windows(source, 8))
        self.assertEqual(debug["pressure_range"], (100.0, 200.0))
        self.assertEqual(debug["pressure_scale"], 100)
        sampled["pressure_scale"] = 200
        with self.assertRaisesRegex(ValueError, "pressure contract"):
            preservation(source, sampled)

    def test_existing_padding_and_missing_nan_are_excluded(self):
        original = sample()
        padded = pad(original, len(original["values"]) + 20)
        padded["values"][padded["padding_mask"]] = np.nan
        padded["values"][0, 3] = np.nan
        padded["feature_mask"][0, 3] = False
        batch = collate([padded])
        self.assertEqual(batch["lengths"].item(), len(original["values"]))
        self.assertTrue(torch.isfinite(batch["observed"]).all())
        padded["padding_mask"][2] = True
        with self.assertRaisesRegex(ValueError, "padding"):
            collate([padded])

    def test_loss_filters_before_arithmetic_and_empty_nan_has_zero_gradient(self):
        batch = collate([sample()])
        batch["augmentation_mask"][0, 1, 0] = True
        prediction = torch.full_like(batch["target"][..., :4], float("nan"), requires_grad=True)
        with torch.no_grad():
            prediction[0, 1, 0] = 2
        batch["target"][0, 0] = float("nan")
        loss = masked_huber(prediction, batch)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertTrue(torch.isfinite(prediction.grad).all())
        batch["augmentation_mask"].zero_()
        prediction.grad = None
        loss = masked_huber(prediction, batch)
        loss.backward()
        self.assertEqual(float(loss), 0)
        self.assertFalse(prediction.grad.any())

    def test_exact_coverage_union_partial_edges_and_gap(self):
        script = Path(__file__).resolve().parents[1] / "scripts/03_select_windows.py"
        spec = importlib.util.spec_from_file_location("study_audit", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = dict(
            relative_ms=np.array([0, 100, 1000, 1100]),
            raw_points=np.array([[0, 0, 1, t, 1] for t in (0, 100, 1000, 1100)]),
            stroke_boundary=np.array([True, False, True, False]),
        )
        windows = [
            dict(time_bounds_ms=(25, 75)),
            dict(time_bounds_ms=(50, 100)),
            dict(time_bounds_ms=(900, 1050)),
        ]
        self.assertEqual(module.coverage(source, windows, 200), 0.625)

    def test_cpu_cold_resume_and_rejection_preserves_checkpoint(self):
        config = dict(
            batch_size=1, updates=3, checkpoint_step=1, mask_fraction=0.15, learning_rate=0.001
        )
        samples = [sample()]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "synthetic"
            result = execute(
                samples,
                samples,
                output,
                config,
                input_contract=dict(source="synthetic", version="v3"),
                device="cpu",
            )
            self.assertTrue(result["checkpoint_completed_equal"])
            path = output / "checkpoint.pt"
            before = path.read_bytes()
            state = torch.load(path, weights_only=True)
            for key in ("input", "training", "train_windows_sha256"):
                expected = copy.deepcopy(state["contract"])
                expected[key] = {"wrong": True}
                with self.assertRaisesRegex(ValueError, "incompatible"):
                    load_checked(path, expected)
            self.assertEqual(before, path.read_bytes())
            self.assertTrue((output / "best-smoke.pt").exists())
            self.assertEqual(len(json.loads((output / "history.json").read_text())["training"]), 3)
        changed = copy.deepcopy(samples)
        changed[0]["values"][1, 0] += 1
        self.assertNotEqual(sample_fingerprint(samples), sample_fingerprint(changed))


if __name__ == "__main__":
    unittest.main()
