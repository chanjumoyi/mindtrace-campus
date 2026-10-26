"""Formal schedule, cold resume and evaluation regression tests; synthetic only."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
import torch

from mindtrace_ml import pretraining
from mindtrace_ml.model import BiGRU, collate, mask_batch, masked_huber, target_mask


class FormalTests(unittest.TestCase):
    def samples(self):
        rng = np.random.default_rng(7)
        return [
            dict(
                values=rng.normal(size=(n, 5)).astype(np.float32),
                feature_mask=np.ones((n, 5), dtype=bool),
                stroke_boundary=np.arange(n) == 0,
            )
            for n in (12, 18, 15)
        ]

    def config(self):
        return dict(
            seed=42,
            batch_size=2,
            learning_rate=0.001,
            weight_decay=0.01,
            max_epochs=3,
            patience=7,
            min_delta=0,
            mask_fraction=0.15,
            gradient_clip=1,
            gradient_accumulation=2,
            validation_seed=1042,
        )

    def test_early_stopping_strict_seven_and_ties(self):
        rows = [dict(epoch=i + 1, validation=dict(huber=v)) for i, v in enumerate([2, 1] + [1] * 7)]
        self.assertFalse(pretraining.early_stop(rows[:-1], 7)[2])
        self.assertEqual(pretraining.early_stop(rows, 7), (1, 2, True))

    def test_fixed_evaluation_weighted_and_finite(self):
        torch.set_num_threads(1)
        model = BiGRU()
        samples = self.samples()
        first = pretraining.evaluate(model, samples, self.config(), "cpu", 10)
        second = pretraining.evaluate(model, samples, self.config(), "cpu", 10)
        self.assertEqual(first, second)
        self.assertEqual(sum(v["targets"] for v in first["channels"].values()), first["targets"])
        self.assertAlmostEqual(
            sum(v["huber"] * v["targets"] for v in first["channels"].values()) / first["targets"],
            first["huber"],
        )

    def test_cold_epoch_resume_matches_uninterrupted_and_rejects_change(self):
        samples, config = self.samples(), self.config()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            _, history = pretraining.train(
                samples, samples, root / "full", config, {"source": "synthetic"}, "cpu"
            )
            actual_save = pretraining.save

            def interrupted(path, value):
                actual_save(path, value)
                if path.name == "last.pt":
                    raise RuntimeError("simulated process interruption")

            with (
                patch.object(pretraining, "save", interrupted),
                self.assertRaisesRegex(RuntimeError, "simulated"),
            ):
                pretraining.train(
                    samples, samples, root / "resumed", config, {"source": "synthetic"}, "cpu"
                )
            _, restored = pretraining.train(
                samples,
                samples,
                root / "resumed",
                config,
                {"source": "synthetic"},
                "cpu",
                resume=True,
            )
            self.assertEqual(
                [r["train_huber"] for r in history], [r["train_huber"] for r in restored]
            )
            a = torch.load(root / "full/last.pt", weights_only=True)
            b = torch.load(root / "resumed/last.pt", weights_only=True)
            for name in a["model"]:
                torch.testing.assert_close(a["model"][name], b["model"][name], rtol=0, atol=0)
            with self.assertRaisesRegex(ValueError, "incompatible"):
                pretraining.train(
                    samples,
                    samples,
                    root / "resumed",
                    config,
                    {"source": "changed"},
                    "cpu",
                    resume=True,
                )
            self.assertTrue(
                json.loads((root / "full/frozen.json").read_text())["test_used_for_selection"]
                is False
            )

    def test_all_missing_has_no_targets_and_zero_finite_gradient(self):
        sample = self.samples()[0]
        sample["feature_mask"][:] = False
        batch = mask_batch(collate([sample]), torch.Generator().manual_seed(7))
        prediction = torch.randn(1, 12, 4, requires_grad=True)
        loss = masked_huber(prediction, batch)
        loss.backward()
        self.assertEqual(int(target_mask(batch).sum()), 0)
        self.assertEqual(float(loss), 0)
        self.assertTrue(torch.isfinite(prediction.grad).all())


if __name__ == "__main__":
    unittest.main()
