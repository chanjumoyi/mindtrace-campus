"""PR #4 regressions using only synthetic trajectories and manifests."""

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np

from mindtrace_ml.windowing import point_windows, prepare

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/03_select_windows.py"
SPEC = importlib.util.spec_from_file_location("pr4_window_study", SCRIPT)
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)


def plan():
    return json.loads((SCRIPT.parents[1] / "configs/window-study.json").read_text())


def records():
    return [
        dict(source_id=f"{split}/{writer}/{index}", writer_id=writer, split=split)
        for split in ("train", "val")
        for writer in ("b", "a")
        for index in range(3)
    ]


class ReviewTests(unittest.TestCase):
    def test_each_debug_window_has_no_predecessor_speed_and_keeps_interior(self):
        t = np.arange(12) * 2
        points = np.column_stack([t, t * 2, np.ones(12), t, np.ones(12)])
        source = prepare(points, dict(origin=[0, 0], scale=[100, 100]))
        before = source["speed"].copy()
        self.assertTrue(source["speed_valid"][4])
        for offset, window in enumerate(point_windows(source, size=4)):
            self.assertFalse(window["speed_valid"][0])
            self.assertEqual(window["speed"][0], 0)
            np.testing.assert_array_equal(
                window["speed"][1:], before[offset * 4 + 1 : offset * 4 + 4]
            )
            self.assertTrue(window["speed_valid"][1:].all())
        np.testing.assert_array_equal(source["speed"], before)
        self.assertTrue(source["speed_valid"][4])

    def test_manifest_rejects_missing_extra_duplicate_and_changed_identity(self):
        original = records()
        reference = {r["source_id"]: r for r in original}
        study.validate_manifest(list(reversed(original)), reference)
        changes = [
            original[:-1],
            original + [dict(source_id="extra", split="val", writer_id="x")],
            original + [original[0]],
        ]
        for key, value in (("writer_id", "wrong"), ("split", "val"), ("split", "test")):
            changed = copy.deepcopy(original)
            changed[0][key] = value
            changes.append(changed)
        for changed in changes:
            with self.subTest(changed=changed[0]), self.assertRaisesRegex(ValueError, "manifest"):
                study.validate_manifest(changed, reference)

    def test_records_per_writer_changes_actual_selection_and_rejects_shortage(self):
        p = plan()
        p["smoke"].update(train_writers=1, val_writers=1, records_per_writer=1)
        selected = study.smoke_sources(records(), p)
        self.assertEqual(selected, {"train/a/0", "val/a/0"})
        p["smoke"]["records_per_writer"] = 2
        self.assertEqual(study.smoke_sources(records(), p), selected | {"train/a/1", "val/a/1"})
        p["smoke"]["records_per_writer"] = 4
        with self.assertRaisesRegex(ValueError, "insufficient"):
            study.smoke_sources(records(), p)

    def test_unsupported_fixed_policies_and_invalid_counts_are_rejected(self):
        original = plan()
        study.validate_plan(original)
        for key in study.FIXED_POLICIES:
            changed = copy.deepcopy(original)
            target = (
                changed["selection"]
                if key in ("aggregation", "eligible_order", "fallback")
                else changed
            )
            target[key] = "unimplemented policy"
            with (
                self.subTest(policy=key),
                self.assertRaisesRegex(ValueError, "unsupported study policy"),
            ):
                study.validate_plan(changed)
        for value in (0, -1, True, 1.5):
            changed = copy.deepcopy(original)
            changed["smoke"]["records_per_writer"] = value
            with self.assertRaisesRegex(ValueError, "positive integer"):
                study.validate_plan(changed)


if __name__ == "__main__":
    unittest.main()
