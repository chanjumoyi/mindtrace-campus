"""PR #3 regressions; all files and trajectories are synthetic."""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mindtrace_ml.features import VERSION as FEATURES_VERSION
from mindtrace_ml.features import extract
from mindtrace_ml.trajectory import VERSION, pad, pressure_parameters, transform, windows

ROOT = Path(__file__).resolve().parents[1]

COORD = dict(origin=[0, 0], scale=[2, 2])
POINTS = np.array([[0, 0, 100, 0, 1], [1, 1, 150, 100, 1], [2, 2, 200, 200, 1]], dtype=float)


class ReviewFixTests(unittest.TestCase):
    def test_all_point_arrays_padded_with_unambiguous_sentinels(self):
        record = transform(POINTS, COORD, [100, 200])
        window = next(windows(record, 150, 100))
        padded = pad(window, 4)
        for name, original in window.items():
            if isinstance(original, np.ndarray):
                self.assertEqual(len(padded[name]), 4, name)
                np.testing.assert_equal(padded[name][:2], original)
                self.assertEqual(len(window[name]), 2, "input mutated")
        self.assertTrue(np.isnan(padded["raw_points"][2:]).all())
        self.assertTrue(np.isnan(padded["epoch_ms"][2:]).all())
        np.testing.assert_equal(padded["source_indices"][2:], [-1, -1])
        np.testing.assert_equal(padded["source_spans"][2:], [[-1, -1], [-1, -1]])
        self.assertFalse(padded["speed_valid"][2:].any())
        self.assertFalse(padded["measurement_missing"][2:].any())
        self.assertTrue(padded["padding_mask"][2:].all())
        self.assertEqual(padded["pressure_range"], (100.0, 200.0))
        self.assertEqual(padded["version"], VERSION)
        loaded = {
            key: np.asarray(value) if not isinstance(value, dict) else json.dumps(value)
            for key, value in window.items()
        }
        loaded_padded = pad(loaded, 4)
        np.testing.assert_equal(loaded_padded["time_bounds_ms"], [0, 150])
        np.testing.assert_equal(loaded_padded["pressure_range"], [100, 200])
        self.assertEqual(str(loaded_padded["version"]), VERSION)
        window["broken"] = np.zeros(3)
        with self.assertRaisesRegex(ValueError, "length mismatch"):
            pad(window, 4)

    def test_pressure_range_is_configured_and_shared_with_features(self):
        with patch(
            "mindtrace_ml.trajectory.config",
            return_value={"ouhd_l": {"pressure_range": [100, 200]}},
        ):
            record = transform(POINTS, COORD)
        np.testing.assert_allclose(record["values"][:, 3], [0, 0.5, 1])
        self.assertAlmostEqual(extract(record)["values"]["pressure_mean"], 0.5)
        points = POINTS.copy()
        points[0, 2], points[-1, 2] = 99, 201
        record = transform(points, COORD, [100, 200])
        np.testing.assert_equal(record["feature_mask"][:, 3], [False, True, False])
        browser = POINTS.copy()
        browser[:, 2] = [0, 0.5, 1]
        np.testing.assert_allclose(transform(browser, COORD, [0, 1])["values"][:, 3], [0, 0.5, 1])
        for bounds in ([1, 1], [1, 0], [0, np.nan], [0], [0, np.inf]):
            with self.assertRaises(ValueError):
                pressure_parameters(bounds)

    def test_synthetic_run_metadata_and_portable_npz_agree(self):
        spec = importlib.util.spec_from_file_location(
            "prepare_review_test", ROOT / "scripts/01_prepare_data.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        settings = {"ouhd_l": {"pressure_range": [100, 200], "permission": "synthetic"}}
        with tempfile.TemporaryDirectory() as temporary, contextlib.ExitStack() as stack:
            root = Path(temporary)
            records = []
            for split in ("train", "val", "test"):
                path = root / f"{split}.txt"
                path.write_text("synthetic")
                records.append(dict(split=split, writer_id=split, path=path, source_id=path.name))
            stack.enter_context(patch.object(module, "ML_ROOT", root))
            stack.enter_context(patch.object(module, "manifest", return_value=records))
            stack.enter_context(
                patch.object(module, "read_points", side_effect=lambda _: POINTS.copy())
            )
            stack.enter_context(patch.object(module, "config", return_value=settings))
            stack.enter_context(patch("mindtrace_ml.trajectory.config", return_value=settings))
            stack.enter_context(patch.object(module, "plot"))
            stack.enter_context(
                patch.object(
                    sys,
                    "argv",
                    ["prepare", "--sample-arrays", "--window-ms", "150", "--stride-ms", "100"],
                )
            )
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            module.main()
            run = next((root / "data/processed/ouhd_l-v1").iterdir())
            summary = json.loads((run / "summary.json").read_text())
            normalization = json.loads((run / "normalization.json").read_text())
            self.assertEqual(summary["status"], "passed")
            self.assertEqual(summary["trajectory_version"], VERSION)
            self.assertEqual(summary["features_version"], FEATURES_VERSION)
            self.assertEqual((summary["window_ms"], summary["stride_ms"]), (150, 100))
            self.assertEqual(
                summary["pressure"], dict(range=[100.0, 200.0], offset=100.0, scale=100.0)
            )
            self.assertEqual(normalization["version"], VERSION)
            self.assertEqual(normalization["normalization_channels"], summary["channels"][:4])
            for key in (
                "trajectory_version",
                "features_version",
                "pressure",
                "window_ms",
                "stride_ms",
            ):
                self.assertEqual(summary[key], normalization[key])
            files = list(run.rglob("*.npz"))
            self.assertEqual(len(files), 3)
            for file in files:
                with np.load(file, allow_pickle=False) as saved:
                    module.validate_saved_window(saved, summary)
                    self.assertEqual(str(saved["schema_version"]), VERSION)
                    self.assertEqual(float(saved["pressure_scale"]), 100.0)
                    for name in saved.files:
                        self.assertFalse(saved[name].dtype.hasobject)

    def test_acceptance_gates_survive_optimized_python(self):
        code = """
import numpy as np
from mindtrace_ml.contracts import run_metadata,validate_features,validate_saved_window
metadata=run_metadata(150,100,dict(range=[0,1],offset=0,scale=1))
valid=dict(values=np.zeros((2,5)),schema_version=metadata['trajectory_version'],features_version=metadata['features_version'],window_ms=150,stride_ms=100)
cases=[lambda: validate_features(dict(values=dict(bad=np.nan))),
       lambda: validate_saved_window(dict(valid,values=np.zeros((2,4))),metadata),
       lambda: validate_saved_window(dict(valid,values=np.full((2,5),np.inf)),metadata),
       lambda: validate_saved_window(dict(valid,schema_version='wrong'),metadata),
       lambda: validate_saved_window(dict(valid,features_version='wrong'),metadata),
       lambda: validate_saved_window(dict(valid,stride_ms=99),metadata),
       lambda: validate_saved_window(dict(valid,bad=np.array({'bad':1},dtype=object)),metadata)]
for check in cases:
    try: check()
    except RuntimeError: pass
    else: raise SystemExit('acceptance gate was bypassed')
print('all gates enforced')
"""
        environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        result = subprocess.run(
            [sys.executable, "-O", "-c", code], env=environment, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("all gates enforced", result.stdout)


if __name__ == "__main__":
    unittest.main()
