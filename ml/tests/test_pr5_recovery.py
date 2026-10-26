"""PR #5 interruption recovery: synthetic CPU checkpoints, no real data/evaluation."""

import importlib.util
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
from mindtrace_ml.checkpoint import fingerprint
from mindtrace_ml.data import sha256

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/04_pretrain.py"
SPEC = importlib.util.spec_from_file_location("pr5_pretrain", SCRIPT)
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "run"
        self.config = json.loads((SCRIPT.parents[1] / "configs/pretraining.json").read_text())
        self.config.update(max_epochs=1, batch_size=2)
        rng = np.random.default_rng(7)
        self.samples = [
            dict(
                values=rng.normal(size=(n, 5)).astype(np.float32),
                feature_mask=np.ones((n, 5), dtype=bool),
                stroke_boundary=np.arange(n) == 0,
            )
            for n in (8, 12, 15)
        ]
        self.input = {"source": "synthetic"}

    def train(self):
        return pretraining.train(
            self.samples, self.samples, self.output, self.config, self.input, "cpu"
        )

    def evaluated(self, summary=True):
        _, history = self.train()
        pretraining.write_json(
            self.output / "test-started.json",
            dict(
                encoder_sha256=sha256(self.output / "encoder.pt"),
                frozen_sha256=sha256(self.output / "frozen.json"),
            ),
        )
        # Deliberately pre-existing metrics: recovery must not perform an evaluation.
        pretraining.write_json(
            self.output / "test-metrics.json",
            dict(
                encoder_sha256=sha256(self.output / "encoder.pt"),
                evaluation_count=1,
                windows=3,
                metrics=dict(huber=0.1, targets=10, mae=0.2, rmse=0.3),
            ),
        )
        if summary:
            pretraining.complete_evaluation(self.output, history)
        return history

    def snapshot(self):
        return {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.output.iterdir()
            if p.is_file()
        }

    def test_completed_resume_preserves_every_file_bytes_and_mtime(self):
        self.evaluated()
        before = self.snapshot()
        with (
            patch.object(pretraining, "BiGRU", side_effect=AssertionError("model constructed")),
            patch.object(
                pretraining, "evaluate", side_effect=AssertionError("evaluation repeated")
            ),
        ):
            self.assertTrue(
                pretraining.resume_completed(self.output, self.config, self.input, "cpu")
            )
            self.assertTrue(
                pretraining.resume_completed(self.output, self.config, self.input, "cpu")
            )
        self.assertEqual(before, self.snapshot())
        with self.assertRaisesRegex(RuntimeError, "already started"):
            pretraining.train(
                self.samples, self.samples, self.output, self.config, self.input, "cpu", resume=True
            )
        self.assertEqual(before, self.snapshot())

    def test_final_checkpoint_interrupt_restores_missing_or_stale_history(self):
        actual_save = pretraining.save

        def interrupted(path, value):
            actual_save(path, value)
            if path.name == "last.pt":
                raise RuntimeError("simulated interruption after terminal checkpoint")

        with (
            patch.object(pretraining, "save", interrupted),
            self.assertRaisesRegex(RuntimeError, "simulated"),
        ):
            self.train()
        self.assertFalse((self.output / "history.json").exists())
        expected = torch.load(self.output / "last.pt", weights_only=True)["history"]
        for previous in (None, []):
            with self.subTest(previous=previous):
                if previous is None:
                    (self.output / "history.json").unlink(missing_ok=True)
                else:
                    pretraining.write_json(self.output / "history.json", previous)
                with patch.object(
                    pretraining, "evaluate", side_effect=AssertionError("training repeated")
                ):
                    _, actual = pretraining.train(
                        self.samples,
                        self.samples,
                        self.output,
                        self.config,
                        self.input,
                        "cpu",
                        resume=True,
                    )
                self.assertEqual(expected, actual)
                self.assertEqual(expected, json.loads((self.output / "history.json").read_text()))

    def test_metrics_written_but_summary_interrupted_repairs_without_evaluation(self):
        history = self.evaluated(summary=False)
        original = pretraining.write_json

        def interrupted(path, value):
            if path.name == "summary.json":
                raise RuntimeError("simulated summary interruption")
            original(path, value)

        with (
            patch.object(pretraining, "write_json", interrupted),
            self.assertRaisesRegex(RuntimeError, "simulated"),
        ):
            pretraining.complete_evaluation(self.output, history)
        self.assertFalse((self.output / "summary.json").exists())
        before = self.snapshot()
        with patch.object(pretraining, "evaluate", side_effect=AssertionError("test repeated")):
            self.assertTrue(
                pretraining.resume_completed(self.output, self.config, self.input, "cpu")
            )
        summary = json.loads((self.output / "summary.json").read_text())
        self.assertTrue(summary["completed"])
        self.assertEqual(summary["test"], dict(huber=0.1, targets=10, mae=0.2, rmse=0.3))
        after = self.snapshot()
        self.assertEqual(before, {k: v for k, v in after.items() if k != "summary.json"})

    def test_early_stopping_checkpoint_also_repairs_history_without_more_epochs(self):
        self.config.update(max_epochs=4, patience=1)
        actual_save = pretraining.save

        def interrupted(path, value):
            actual_save(path, value)
            if path.name == "last.pt" and len(value["history"]) == 2:
                raise RuntimeError("simulated early-stop interruption")

        with (
            patch.object(pretraining, "evaluate", return_value=dict(huber=1.0)),
            patch.object(pretraining, "save", interrupted),
            self.assertRaisesRegex(RuntimeError, "simulated"),
        ):
            self.train()
        self.assertEqual(len(json.loads((self.output / "history.json").read_text())), 1)
        with patch.object(pretraining, "evaluate", side_effect=AssertionError("epoch repeated")):
            _, history = pretraining.train(
                self.samples, self.samples, self.output, self.config, self.input, "cpu", resume=True
            )
        self.assertEqual(len(history), 2)
        self.assertEqual(json.loads((self.output / "history.json").read_text()), history)
        self.assertTrue(json.loads((self.output / "frozen.json").read_text())["early_stopped"])

    def test_completed_run_restores_history_from_checkpoint_without_touching_frozen_files(self):
        expected = self.evaluated()
        (self.output / "history.json").unlink()
        before = self.snapshot()
        self.assertTrue(pretraining.resume_completed(self.output, self.config, self.input, "cpu"))
        self.assertEqual(json.loads((self.output / "history.json").read_text()), expected)
        self.assertEqual(before, {k: v for k, v in self.snapshot().items() if k != "history.json"})

    def test_test_started_without_metrics_blocks_before_any_file_changes(self):
        self.evaluated()
        (self.output / "test-metrics.json").unlink()
        before = self.snapshot()
        with self.assertRaisesRegex(RuntimeError, "previously started"):
            pretraining.resume_completed(self.output, self.config, self.input, "cpu")
        self.assertEqual(before, self.snapshot())

    def test_changed_bindings_or_contract_rejected_without_writes(self):
        self.evaluated()
        for filename in ("encoder.pt", "frozen.json", "test-metrics.json"):
            with self.subTest(filename=filename):
                path = self.output / filename
                original = path.read_bytes()
                if filename == "test-metrics.json":
                    data = json.loads(original)
                    data["encoder_sha256"] = "wrong"
                    pretraining.write_json(path, data)
                else:
                    path.write_bytes(original + b" ")
                before = self.snapshot()
                with self.assertRaisesRegex(ValueError, "binding"):
                    pretraining.resume_completed(self.output, self.config, self.input, "cpu")
                self.assertEqual(before, self.snapshot())
                path.write_bytes(original)
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "incompatible"):
            pretraining.resume_completed(self.output, self.config, {"changed": "source"}, "cpu")
        self.assertEqual(before, self.snapshot())

    def test_cli_completed_gate_precedes_cuda_cache_and_training(self):
        # A small accepted-study metadata fixture exercises the actual main entry point.
        root = self.root / "ml"
        study = root / "study"
        accepted = root / "accepted"
        for folder in (root / "configs", root / "scripts", study, accepted):
            folder.mkdir(parents=True, exist_ok=True)
        fake_script = root / "scripts/04_pretrain.py"
        fake_script.write_text("# synthetic implementation fingerprint\n")
        frozen = dict(preprocessing_version=cli.VERSION, source_metadata={}, pressure={})
        norm = dict(
            fit_split="train", coordinates=dict(fit_split="train"), source_metadata={}, pressure={}
        )
        pretraining.write_json(accepted / "inventory.json", dict(records=[]))
        pretraining.write_json(
            study / "summary.json",
            dict(
                status="passed",
                test_measurements_opened=0,
                input_run=str(accepted),
                inventory_sha256=sha256(accepted / "inventory.json"),
            ),
        )
        pretraining.write_json(study / "normalization.json", norm)
        pretraining.write_json(study / "preprocessing-frozen.json", frozen)
        pretraining.write_json(root / "configs/preprocessing-frozen.json", frozen)
        pretraining.write_json(root / "configs/pretraining.json", self.config)
        self.input = dict(
            source=dict(
                frozen=frozen,
                normalization=norm,
                study_summary_sha256=sha256(study / "summary.json"),
                inventory_sha256=sha256(accepted / "inventory.json"),
                manifest_sha256=fingerprint([]),
                implementation_sha256={str(fake_script.relative_to(root)): sha256(fake_script)},
            ),
            cache_sha256={},
        )
        self.evaluated(summary=False)
        pretraining.write_json(self.output / "input-contract.json", self.input)
        before = self.snapshot()

        def on_cpu(output, config, contract):
            return pretraining.resume_completed(output, config, contract, "cpu")

        with (
            patch.object(cli, "ML_ROOT", root),
            patch.object(cli, "__file__", str(fake_script)),
            patch.object(cli, "manifest", return_value=[]),
            patch.object(cli, "resume_completed", side_effect=on_cpu),
            patch.object(cli, "cached", side_effect=AssertionError("cache loaded")),
            patch.object(cli, "train", side_effect=AssertionError("training repeated")),
            patch.object(cli, "evaluate", side_effect=AssertionError("test repeated")),
            patch.object(cli.torch.cuda, "is_available", side_effect=AssertionError("GPU checked")),
            patch.object(
                sys,
                "argv",
                [
                    "04_pretrain.py",
                    "--study-run",
                    str(study),
                    "--output",
                    str(self.output),
                    "--resume",
                ],
            ),
        ):
            cli.main()
        after = self.snapshot()
        self.assertEqual(before, {k: v for k, v in after.items() if k != "summary.json"})
        self.assertTrue(json.loads((self.output / "summary.json").read_text())["completed"])


if __name__ == "__main__":
    unittest.main()
