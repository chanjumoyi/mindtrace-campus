"""Synthetic engineering and model invariants; no participant fixtures."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import torch
from mindtrace_ml.model import BiGRU, collate, mask_batch, masked_huber
from mindtrace_ml.trajectory import Standardizer
from mindtrace_ml.windowing import point_windows, prepare, preservation, time_windows

COORD = dict(origin=[0, 0], scale=[100, 100])


def line(rate=500, duration=2500):
    t = np.arange(0, duration + 1, 1000 / rate)
    return np.column_stack([t / 100, t / 200, np.full(len(t), 1000), t, np.ones(len(t))])


class InputTests(unittest.TestCase):
    def test_resampling_same_duration_across_rates(self):
        a = prepare(line(500, 2800), COORD, 125)
        b = prepare(line(125, 2800), COORD, 125)
        np.testing.assert_allclose(a["values"], b["values"], atol=1e-12)
        w = list(time_windows(a))
        self.assertEqual(len(w[0]["values"]), 250)
        self.assertFalse(w[0]["feature_mask"][0, :3].any())
        self.assertEqual(w[0]["time_bounds_ms"], (0, 2000))
        self.assertEqual(len(list(time_windows(a, short_minimum_ms=2000))), 1)
        self.assertEqual(len(list(time_windows(a, short_minimum_ms=500))), 2)
        self.assertTrue(all(len(x["values"]) <= 256 for x in point_windows(a)))

    def test_no_pen_up_or_gap_interpolation_and_provenance(self):
        p = np.array(
            [
                [0, 0, 100, 0, 1],
                [1, 0, 200, 8, 1],
                [2, 0, 0, 8, 0],
                [30, 0, 0, 1000, 0],
                [40, 0, 300, 1000, 1],
                [41, 0, 400, 1008, 1],
                [80, 0, 500, 2000, 1],
                [81, 0, 600, 2008, 1],
            ]
        )
        r = prepare(p, COORD, 250)
        t = r["source_time_ms"]
        self.assertFalse(((t > 8) & (t < 1000)).any())
        self.assertFalse(((t > 1008) & (t < 2000)).any())
        self.assertEqual(np.sum(t == 8), 2)
        self.assertEqual(np.sum(t == 1000), 2)
        np.testing.assert_equal(r["raw_points"][r["stroke_boundary"], 3], [0, 8, 1000, 1000, 2000])
        self.assertFalse(r["feature_mask"][r["stroke_boundary"], :2].any())
        left, right = r["source_left_spans"][:, 0], r["source_right_spans"][:, 0]
        alpha = r["source_alpha"][:, None]
        np.testing.assert_allclose(
            r["raw_points"][:, :2], p[left, :2] * (1 - alpha) + p[right, :2] * alpha
        )
        self.assertTrue(np.isfinite(r["values"]).all())

    def test_resampling_missing_pressure_and_preservation(self):
        p = line()
        source = prepare(p, COORD)
        sampled = prepare(p, COORD, 125)
        metrics = preservation(source, sampled)
        self.assertLess(metrics["position_p95"], 1e-12)
        self.assertLess(metrics["pressure_p95"], 1e-12)
        p[1, 2] = np.nan
        r = prepare(p[:5], COORD, 1000)
        self.assertFalse(r["feature_mask"][1:4, 3].any())

    def test_model_padding_mask_loss_and_no_target_leak(self):
        torch.set_num_threads(2)
        r = prepare(line(duration=64), COORD)
        scaler = Standardizer().fit([("train", r)])
        r["values"] = scaler.apply(r["values"], r["feature_mask"])
        short = {k: v[:8] if isinstance(v, np.ndarray) else v for k, v in r.items()}
        batch = mask_batch(collate([r, short]), torch.Generator().manual_seed(42))
        self.assertTrue(batch["augmentation_mask"].any())
        self.assertFalse(batch["observed"][batch["augmentation_mask"]].any())
        self.assertFalse(batch["augmentation_mask"][batch["padding_mask"]].any())
        selected = torch.nonzero(batch["augmentation_mask"][0].any(dim=-1)).flatten()
        self.assertTrue((torch.diff(selected) == 1).all())
        model = BiGRU().eval()
        with torch.no_grad():
            prediction, pool = model(batch)
            changed = {k: v.clone() for k, v in batch.items()}
            changed["observed"][changed["padding_mask"]] = 999
            a, b = model(changed)
            torch.testing.assert_close(prediction, a)
            torch.testing.assert_close(pool, b)
            alone = mask_batch(collate([short]), torch.Generator().manual_seed(1))
            alone["observed"][0] = batch["observed"][1, :8]
            alone["augmentation_mask"][0] = batch["augmentation_mask"][1, :8]
            torch.testing.assert_close(model(alone)[1][0], pool[1], atol=1e-6, rtol=1e-5)
        target_mask = batch["augmentation_mask"][..., :4]
        corrupt = prediction.clone()
        corrupt[~target_mask] = 1e6
        torch.testing.assert_close(masked_huber(prediction, batch), masked_huber(corrupt, batch))
        batch["augmentation_mask"].zero_()
        zero = masked_huber(prediction.requires_grad_(), batch)
        zero.backward()
        self.assertEqual(float(zero), 0)
        self.assertFalse(prediction.grad.any())
        missing = collate([r])
        missing["feature_mask"].zero_()
        missing["target"].zero_()
        missing["observed"].zero_()
        missing["measurement_missing"] = ~missing["padding_mask"].unsqueeze(-1).expand_as(
            missing["feature_mask"]
        )
        missing = mask_batch(missing, torch.Generator().manual_seed(42))
        self.assertFalse(missing["augmentation_mask"].any())
        empty_loss = masked_huber(model(missing)[0], missing)
        self.assertEqual(float(empty_loss), 0)
        empty_loss.backward()
        self.assertTrue(
            all(
                parameter.grad is None or not parameter.grad.any()
                for parameter in model.parameters()
            )
        )

    def test_test_read_guard_and_deterministic_selection(self):
        script = Path(__file__).resolve().parents[1] / "scripts/03_select_windows.py"
        spec = importlib.util.spec_from_file_location("window_study", script)
        study = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(study)
        with (
            patch.object(study, "read_points", side_effect=AssertionError("must not read")),
            self.assertRaisesRegex(ValueError, "test measurements"),
        ):
            study.read_development(dict(split="test"), {})
        plan = dict(
            selection=dict(
                position_p95_max=0.002, pressure_p95_max=0.02, minimum_down_time_coverage=0.99
            )
        )
        common = dict(
            position_p95=0.0, pressure_p95=0.0, coverage=1.0, stride_ms=2000, short_minimum_ms=500
        )
        a, b = dict(common, points=100), dict(common, points=50)
        self.assertEqual(study.select([a, b], plan), b)
        b["coverage"] = 0.9
        self.assertEqual(study.select([a, b], plan), a)
        a["coverage"] = 0.9
        with self.assertRaises(ValueError):
            study.select([a, b], plan)


if __name__ == "__main__":
    unittest.main()
