"""Synthetic fixtures only. Run unittest discover from the repository root."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mindtrace_ml.data import manifest
from mindtrace_ml.features import extract
from mindtrace_ml.trajectory import (
    Quarantine,
    Standardizer,
    browser_pressure_mask,
    fit_coordinates,
    pad,
    repair,
    transform,
    windows,
)

COORD = dict(origin=[0, 0], scale=[10, 10])


class PipelineTests(unittest.TestCase):
    def test_browser_pressure_requires_pen_and_dynamic_down_range(self):
        self.assertFalse(browser_pressure_mask([0, 1], ["mouse", "mouse"], [True, True]).any())
        self.assertFalse(browser_pressure_mask([0.5, 0.505], ["pen", "pen"], [True, True]).any())
        self.assertTrue(browser_pressure_mask([0.5, 0.51], ["pen", "pen"], [True, True]).all())
        self.assertFalse(
            browser_pressure_mask([0, 0.5, 0.5], ["pen"] * 3, [False, True, True]).any()
        )

    def test_large_duplicate_groups_match_arithmetic(self):
        # Exercises the real-data sized reduction path without private fixtures.
        n = 20000
        p = np.column_stack(
            [np.arange(n), np.arange(n) * 2, np.full(n, 100), (np.arange(n) // 2) * 2, np.ones(n)]
        )
        fixed, spans, quality = repair(p)
        self.assertEqual(quality["merged_points"], n // 2)
        np.testing.assert_allclose(fixed[:, 0], np.arange(0, n, 2) + 0.5)
        np.testing.assert_allclose(fixed[:, 1], (np.arange(0, n, 2) + 0.5) * 2)
        np.testing.assert_equal(spans[-1], [n - 2, n])

    def test_duplicate_transition_missing_and_reverse(self):
        raw = np.array(
            [[0, 0, np.nan, 0, 0], [2, 4, np.nan, 0, 0], [3, 5, 4095, 0, 1], [4, 6, 2048, 2, 1]]
        )
        fixed, spans, quality = repair(raw)
        np.testing.assert_equal(fixed[0, :2], [1, 2])
        np.testing.assert_equal(spans[0], [0, 2])
        self.assertEqual(quality, dict(merged_points=1, zero_dt_transitions=1))
        record = transform(raw, COORD)
        self.assertFalse(record["feature_mask"][0, 3])
        self.assertFalse(record["speed_valid"][1])
        self.assertTrue(record["stroke_boundary"][1])
        self.assertEqual(record["values"][1, 2], 0)
        self.assertTrue(np.isfinite(record["values"]).all())
        self.assertTrue(np.isnan(record["epoch_ms"]).all())
        np.testing.assert_equal(record["source_time_ms"], [0, 0, 2])
        with self.assertRaises(Quarantine):
            repair(raw[::-1])

    def test_units_geometry_and_features(self):
        raw = np.array([[0, 0, 0, 0, 1], [3, 4, 4095, 1000, 1], [6, 8, 4095, 2000, 1]])
        r = transform(raw, COORD)
        self.assertEqual(r["values"][1, 2], 1)
        self.assertAlmostEqual(r["speed"][1], 0.5)
        f = extract(r)
        self.assertEqual(len(f["values"]), 28)
        self.assertAlmostEqual(f["values"]["path_length_normalized"], 1)
        self.assertAlmostEqual(f["values"]["straightness"], 1)
        self.assertTrue(all(f["feature_mask"].values()))
        np.testing.assert_allclose(
            r["normalized_xy"] * COORD["scale"] + COORD["origin"], raw[:, :2]
        )

    def test_train_only_inverse_windows_padding(self):
        raw = np.array([[0, 0, 0, 0, 1], [3, 4, 4095, 1000, 1], [6, 8, 4095, 2000, 1]])
        coord = fit_coordinates([("train", raw)])
        with self.assertRaises(ValueError):
            fit_coordinates([("test", raw)])
        record = transform(raw, coord)
        normalizer = Standardizer().fit([("train", record)])
        with self.assertRaises(ValueError):
            Standardizer().fit([("val", record)])
        z = normalizer.apply(record["values"], record["feature_mask"])
        inverse = normalizer.inverse(z)
        np.testing.assert_allclose(
            inverse[record["feature_mask"]], record["values"][record["feature_mask"]]
        )
        chunks = list(windows(record))
        self.assertEqual([len(c["values"]) for c in chunks], [2, 1])
        np.testing.assert_equal(chunks[1]["source_indices"], [2])
        padded = pad(chunks[0], 4)
        np.testing.assert_equal(padded["padding_mask"], [False, False, True, True])
        self.assertFalse(padded["feature_mask"][2:].any())
        self.assertFalse(padded["augmentation_mask"].any())
        with self.assertRaises(ValueError):
            pad(chunks[0], 1)

    def test_manifest_split_missing_and_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for split, writer in [("train", "a"), ("val", "b"), ("test", "c")]:
                (root / f"{split}.txt").write_text("synthetic")
                with (root / f"{split}.csv").open("w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["writer_id", "csv"])
                    w.writeheader()
                    w.writerow(dict(writer_id=writer, csv=f"{split}.txt"))
            self.assertEqual(len(manifest(root)), 3)
            (root / "val.csv").write_text("writer_id,csv\na,val.txt\n")
            with self.assertRaisesRegex(ValueError, "crosses"):
                manifest(root)
            (root / "val.csv").write_text("writer_id,csv\nb,missing.txt\n")
            with self.assertRaisesRegex(ValueError, "missing"):
                manifest(root)
            (root / "val.csv").write_text("writer_id,csv\nb,../escape.txt\n")
            with self.assertRaises(ValueError):
                manifest(root)

    def test_csv_measurements_and_read_only_hash(self):
        from mindtrace_ml.data import read_points, sha256

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.csv"
            names = [f"column{i}" for i in range(23)]
            for index, name in zip(
                (0, 1, 2, 7, 22),
                ("X cood.", "Y cood.", "Pressure", "Time", "pen_down"),
                strict=False,
            ):
                names[index] = name
            header = ",".join(names)
            row = ["0"] * 23
            row[2] = ""
            row[7] = "123"
            row[22] = "1"
            path.write_text(header + "\n" + ",".join(row) + "\n")
            before = sha256(path)
            points = read_points(path)
            self.assertTrue(np.isnan(points[0, 2]))
            self.assertEqual(points[0, 3], 123)
            self.assertEqual(sha256(path), before)

    def test_pause_missing_and_no_interstroke_distance(self):
        raw = np.array(
            [
                [0, 0, np.nan, 0, 1],
                [1, 0, np.nan, 100, 1],
                [100, 0, np.nan, 200, 0],
                [200, 0, np.nan, 800, 1],
                [201, 0, np.nan, 900, 1],
            ]
        )
        f = extract(transform(raw, COORD))
        self.assertAlmostEqual(f["values"]["path_length_normalized"], 0.2)
        self.assertFalse(f["feature_mask"]["pressure_mean"])
        self.assertEqual(f["values"]["pause_count_500ms"], 1)
        self.assertEqual(f["values"]["pause_count_1000ms"], 0)


if __name__ == "__main__":
    unittest.main()
