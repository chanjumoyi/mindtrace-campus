"""Synthetic tests for EMOTHAW identity, quality, gates and regression plumbing."""

import copy
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

from mindtrace_ml.checkpoint import MODEL_CONFIG
from mindtrace_ml.data import sha256
from mindtrace_ml.emothaw import HEADERS, SVC_COLUMNS, audit, label_rows, participant_key, read_svc
from mindtrace_ml.emothaw_permissions import readiness, require_ready
from mindtrace_ml.model import BiGRU, collate
from mindtrace_ml.supervised_pipeline import RegressionPipeline, aggregate_windows, nested_folds


def labels():
    return label_rows(
        [
            list(HEADERS),
            [1, 3, 5, 7, "collector", 1, "Collection1"],
            [2, 1, 2, 3, "collector", 1, "Collection2"],
        ]
    )


class AdapterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.data = self.root / "extracted/DataEmothaw"
        self.data.mkdir(parents=True)
        (self.data / "DASS_scores.xls").write_bytes(b"synthetic workbook placeholder")
        self.source = self.data / "Collection1/user00001/session00001"
        self.source.mkdir(parents=True)

    def trajectory(self, task=1, suffix="", text=None, filename_user=1):
        path = self.source / f"u{filename_user:05d}s00001_hw{task:05d}{suffix}.svc"
        path.write_text(text or "3\n0 0 0 1 0 0 10\n1 2 8 1 0 0 11\n2 4 16 0 0 0 0\n")
        return path

    def run_audit(self):
        with patch("mindtrace_ml.emothaw.read_labels", return_value=labels()):
            return audit(self.root)

    def test_composite_key_keeps_collections_separate_and_scores_raw(self):
        result = labels()
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[("Collection1", 1)]["raw_scores"], dict(depression=3, anxiety=5, stress=7)
        )
        self.assertEqual(participant_key("Collection2", 1.0), ("Collection2", 1))
        self.assertFalse(result[("Collection1", 1)]["classification_enabled"])

    def test_bad_label_keys_duplicates_and_scores_rejected(self):
        valid = [list(HEADERS), [1, 3, 5, 7, "collector", 1, "Collection1"]]
        for changed in ([valid[0], valid[1], valid[1]], [valid[0], valid[1][:-1]]):
            with self.assertRaises(ValueError):
                label_rows(changed)
        for position, value in (
            (1, float("nan")),
            (1, 43),
            (1, "3"),
            (5, 1.5),
            (6, "../Collection1"),
        ):
            changed = copy.deepcopy(valid)
            changed[1][position] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                label_rows(changed)

    def test_count_reversal_and_state_issues_keep_raw_order(self):
        path = self.trajectory(text="4\n0 0 9 1 0 0 10\n1 2 8 2 0 0 11\n")
        result = read_svc(path)
        self.assertEqual(
            result["issues"], ["declared_count_mismatch", "invalid_pen_state", "reversed_time"]
        )
        np.testing.assert_array_equal(result["points"][:, 2], [9, 8])

    def test_missing_pressure_is_distinct_from_true_zero_and_duplicate_time(self):
        path = self.trajectory(text="2\n0 0 0 1 0 0 nan\n1 2 0 0 0 0 0\n")
        result = read_svc(path)
        self.assertEqual(result["issues"], [])
        np.testing.assert_array_equal(result["pressure_valid"], [False, True])
        self.assertEqual(result["duplicate_timestamps"], 1)
        self.assertIsNone(result["units"]["epoch_ms"])

    def test_malformed_width_rejected(self):
        with self.assertRaisesRegex(ValueError, "width"):
            read_svc(self.trajectory(text="1\n1 2 3\n"))

    def test_single_root_duplicate_copy_and_missing_participant_not_independent(self):
        for task in range(1, 8):
            self.trajectory(task)
        self.trajectory(1, suffix=" - Copie")
        outside = self.root.parent / (self.root.name + "-other.svc")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        outside.write_text("not canonical")
        before = {p: sha256(p) for p in self.root.rglob("*") if p.is_file()}
        result = self.run_audit()
        self.assertEqual(result["summary"]["trajectory_files"], 8)
        self.assertEqual(result["summary"]["selected_task_candidates"], 7)
        # Identical contents under different task IDs require review, never become extra people.
        self.assertEqual(len(result["participants"]), 2)
        self.assertTrue(all(not p["formal_supervision_eligible"] for p in result["participants"]))
        self.assertIn("missing_trajectory_directory", result["participants"][1]["issues"])
        self.assertEqual(before, {p: sha256(p) for p in before})

    def test_revised_variant_identity_conflict_and_note_require_review(self):
        for task in range(1, 8):
            self.trajectory(task, text=f"2\n0 0 0 1 0 0 {task}\n1 2 8 1 0 0 {task + 1}\n")
        self.trajectory(2, suffix="_old", text="2\n0 0 0 1 0 0 20\n1 2 8 1 0 0 30\n")
        self.trajectory(3, filename_user=2)
        (self.source / "readme.txt").write_text("source correction note")
        result = self.run_audit()
        reasons = result["participants"][0]["issues"]
        self.assertIn("revised_variant_pending_review", reasons)
        self.assertIn("filename_directory_identity_conflict", reasons)
        self.assertIn("source_note_requires_review", reasons)
        self.assertIn("ambiguous_task_version", reasons)
        self.assertFalse(result["participants"][0]["internal_pipeline_eligible"])

    def test_trajectory_without_label_fails_instead_of_row_order_join(self):
        self.source = self.data / "Collection1/user00002/session00001"
        self.source.mkdir(parents=True)
        self.trajectory(filename_user=2)
        with self.assertRaisesRegex(ValueError, "composite label"):
            self.run_audit()

    def test_cross_participant_content_duplicates_isolate_both(self):
        self.trajectory()
        self.source = self.data / "Collection2/user00001/session00001"
        self.source.mkdir(parents=True)
        self.trajectory()
        result = self.run_audit()
        self.assertTrue(
            all(
                "content_duplicate_across_tasks_or_participants" in p["issues"]
                for p in result["participants"]
            )
        )


class EvidenceTests(unittest.TestCase):
    def test_missing_evidence_blocks_without_training(self):
        self.assertEqual(readiness()["status"], "blocked")
        with self.assertRaises(PermissionError):
            require_ready()

    def test_readiness_cli_does_not_read_trajectories_and_reports_not_started(self):
        script = Path(__file__).resolve().parents[1] / "scripts/05_adapt_emothaw.py"
        spec = importlib.util.spec_from_file_location("emothaw_cli_test", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with (
            patch.object(sys, "argv", [str(script), "--formal-readiness"]),
            patch.object(module, "audit", side_effect=AssertionError("trajectories read")),
            patch("builtins.print") as output,
        ):
            self.assertEqual(module.main(), 2)
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["formal_training_reminder"], "还未展开正式训练")

    def test_document_fingerprint_and_raw_workbook_are_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            doc = root / "evidence.txt"
            doc.write_text("synthetic attestation")
            workbook = root / "labels.xls"
            workbook.write_bytes(b"synthetic")
            item = dict(
                status="verified",
                reviewed_by="synthetic-reviewer",
                reviewed_at="2026-10-26",
                document=dict(path="evidence.txt", sha256=sha256(doc)),
            )
            evidence = {
                k: copy.deepcopy(item)
                for k in (
                    "written_authorization",
                    "mirror_scoring",
                    "source_schema",
                    "existing_exploration",
                )
            }
            evidence["written_authorization"]["scope"] = ["supervised_training"]
            evidence["mirror_scoring"].update(
                instrument="I-DASS-42", conversion="none", workbook_sha256=sha256(workbook)
            )
            evidence["source_schema"].update(
                columns=list(SVC_COLUMNS),
                time_unit="ms",
                coordinate_units="synthetic",
                pressure_range=[0, 100],
            )
            path = root / "evidence.json"
            path.write_text(json.dumps(evidence))
            self.assertEqual(require_ready(path, workbook)["status"], "ready_for_preregistration")
            workbook.write_bytes(b"changed")
            self.assertIn(
                "mirror_workbook_scoring_not_verified", readiness(path, workbook)["reasons"]
            )
            doc.write_text("changed")
            self.assertNotEqual(readiness(path, workbook)["status"], "ready_for_preregistration")


class PipelineTests(unittest.TestCase):
    def test_grouped_nested_splits_reproducible_and_no_window_leakage(self):
        keys = [("Collection1", i) for i in range(1, 21)] * 7
        plan = nested_folds(keys)
        self.assertEqual(plan, nested_folds(list(reversed(keys))))
        all_test = []
        for fold in plan:
            self.assertFalse(set(fold["train"]) & set(fold["test"]))
            all_test += fold["test"]
            for inner in fold["inner"]:
                self.assertFalse(set(inner["train"]) & set(inner["test"]))
                self.assertFalse(set(fold["test"]) & (set(inner["train"]) | set(inner["test"])))
        self.assertEqual(len(all_test), 20)
        self.assertEqual(len(set(all_test)), 20)
        with self.assertRaises(ValueError):
            nested_folds([("Collection1", 1)] * 7)

    def test_task_equal_weighting_not_window_count_and_missing_rejected(self):
        rows = [dict(participant=("Collection1", 1), task=1, features=[0.0]) for _ in range(10)]
        rows.append(dict(participant=("Collection1", 1), task=2, features=[10.0]))
        self.assertEqual(aggregate_windows(rows, (1, 2))[("Collection1", 1)][0], 5)
        with self.assertRaisesRegex(ValueError, "missing"):
            aggregate_windows(rows)
        rows[-1]["session"] = 2
        with self.assertRaisesRegex(ValueError, "sessions"):
            aggregate_windows(rows, (1, 2))

    def test_all_three_encoder_modes_forward_backward_and_freeze_rules(self):
        torch.set_num_threads(1)
        reference = BiGRU()
        pretrained = dict(encoder=reference.encoder.state_dict(), contract=dict(model=MODEL_CONFIG))
        sample = dict(
            values=np.ones((16, 5), dtype=np.float32),
            feature_mask=np.ones((16, 5), bool),
            stroke_boundary=np.arange(16) == 0,
        )
        batch = collate([sample, sample])
        for mode in ("scratch", "frozen_ouhd", "partial_finetune"):
            with self.subTest(mode=mode):
                model = RegressionPipeline(mode, None if mode == "scratch" else pretrained)
                model.train()
                before = {k: v.clone() for k, v in model.backbone.encoder.state_dict().items()}
                optimizer = torch.optim.AdamW(
                    [p for p in model.parameters() if p.requires_grad], lr=0.001
                )
                prediction = model(batch)
                self.assertEqual(prediction.shape, (2, 3))
                loss = torch.nn.functional.mse_loss(prediction, torch.ones(2, 3))
                loss.backward()
                optimizer.step()
                self.assertTrue(torch.isfinite(loss))
                changed = {
                    k
                    for k, v in model.backbone.encoder.state_dict().items()
                    if not torch.equal(v, before[k])
                }
                if mode == "frozen_ouhd":
                    self.assertFalse(changed)
                    self.assertFalse(model.backbone.training)
                elif mode == "partial_finetune":
                    self.assertTrue(changed)
                    self.assertTrue(all("_l1" in k for k in changed))
                else:
                    self.assertTrue(changed)
        with self.assertRaises(ValueError):
            RegressionPipeline("scratch", pretrained)
        with self.assertRaises(ValueError):
            RegressionPipeline("frozen_ouhd")


if __name__ == "__main__":
    unittest.main()
