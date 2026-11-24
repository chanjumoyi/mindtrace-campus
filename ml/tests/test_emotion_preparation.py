"""Synthetic-only tests for the handwriting emotion preparation pipeline."""

from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "emotion" / "src"))

from mindtrace_emotion.features import FEATURE_NAMES, extract_attempt_features
from mindtrace_emotion.labels import (
    CPED_TO_EMOTION,
    TAXONOMY,
    normalize_emotion,
    weak_emotion_from_mood_stress,
)
from mindtrace_emotion.sequence import build_sequence
from mindtrace_emotion.sessions import (
    build_manifest_rows,
    image_estimate,
    json_files,
    load_labels,
    manifest_summary,
)
from mindtrace_emotion.splits import assign_participant_splits


def synthetic_points() -> list[dict]:
    return [
        {
            "seq": 0,
            "strokeId": 1,
            "phase": "down",
            "pointerType": "pen",
            "xNorm": 0.1,
            "yNorm": 0.2,
            "elapsedMs": 0,
            "pressure": 0.3,
        },
        {
            "seq": 1,
            "strokeId": 1,
            "phase": "move",
            "pointerType": "pen",
            "xNorm": 0.2,
            "yNorm": 0.2,
            "elapsedMs": 20,
            "pressure": 0.5,
        },
        {
            "seq": 2,
            "strokeId": 1,
            "phase": "up",
            "pointerType": "pen",
            "xNorm": 0.2,
            "yNorm": 0.2,
            "elapsedMs": 25,
            "pressure": 0.0,
        },
        {
            "seq": 3,
            "strokeId": 2,
            "phase": "down",
            "pointerType": "pen",
            "xNorm": 0.4,
            "yNorm": 0.5,
            "elapsedMs": 600,
            "pressure": 0.4,
        },
        {
            "seq": 4,
            "strokeId": 2,
            "phase": "move",
            "pointerType": "pen",
            "xNorm": 0.5,
            "yNorm": 0.5,
            "elapsedMs": 640,
            "pressure": 0.6,
        },
    ]


def synthetic_session(session_id: str, participant: str, *, excluded: bool = False) -> dict:
    return {
        "schemaVersion": "1.7.0",
        "appVersion": "handwriting-collector-mobile/1.7.0",
        "sessionId": session_id,
        "participantId": participant,
        "datasetEligibility": "excluded_test_record" if excluded else "eligible",
        "attempts": [
            {
                "attemptId": f"{session_id}-COPY-1",
                "attemptNumber": 1,
                "taskId": "COPY_SENTENCE_REPEAT_1",
                "taskTitle": "抄写 1",
                "quality": {"status": "usable"},
                "canvas": {"width": 360, "height": 400, "devicePixelRatio": 3},
                "points": synthetic_points(),
                "image": {
                    "filename": "x.png",
                    "mimeType": "image/png",
                    "dataUrl": "data:image/png;base64,AAAA",
                },
            }
        ],
    }


class EmotionPreparationTests(unittest.TestCase):
    def test_taxonomy_and_aliases(self):
        self.assertEqual(set(TAXONOMY), set(CPED_TO_EMOTION.values()))
        self.assertEqual(normalize_emotion("Depress"), "sadness")
        self.assertEqual(normalize_emotion("worried"), "anxiety")
        self.assertEqual(normalize_emotion("happy"), "positive")
        self.assertIsNone(normalize_emotion("uncertain"))
        self.assertIsNone(normalize_emotion("no-such-label"))

    def test_weak_label_quadrants(self):
        self.assertEqual(weak_emotion_from_mood_stress(5, 1), "positive")
        self.assertEqual(weak_emotion_from_mood_stress(1, 5), "anxiety")
        self.assertEqual(weak_emotion_from_mood_stress(1, 1), "sadness")
        self.assertEqual(weak_emotion_from_mood_stress(5, 5), "other")
        self.assertEqual(weak_emotion_from_mood_stress(3, 3), "neutral")
        self.assertIsNone(weak_emotion_from_mood_stress("x", 3))

    def test_features_are_finite_and_structural(self):
        features = extract_attempt_features({"points": synthetic_points()})
        self.assertEqual(set(features), set(FEATURE_NAMES))
        self.assertEqual(features["point_count"], 5)
        self.assertEqual(features["stroke_count"], 2)
        self.assertAlmostEqual(features["duration_ms"], 640)
        self.assertAlmostEqual(features["bbox_width_norm"], 0.4)
        self.assertAlmostEqual(features["bbox_height_norm"], 0.3)
        self.assertGreater(features["path_length_norm"], 0)
        self.assertAlmostEqual(features["pressure_mean"], (0.3 + 0.5 + 0.4 + 0.6) / 4)
        self.assertGreater(features["pressure_range"], 0.01)
        self.assertEqual(features["between_pause_count"], 1)
        for name in FEATURE_NAMES:
            if name.startswith("tilt_"):
                self.assertTrue(math.isnan(features[name]), name)
            else:
                self.assertTrue(math.isfinite(features[name]), name)

    def test_sequence_shape_and_masks(self):
        sequence = build_sequence(synthetic_points(), max_len=8)
        self.assertEqual(sequence["values"].shape, (8, 5))
        self.assertEqual(sequence["feature_mask"].shape, (8, 5))
        self.assertEqual(sequence["stroke_boundary"].shape, (8,))
        self.assertFalse(sequence["feature_mask"][0, 0])
        self.assertFalse(sequence["feature_mask"][0, 1])
        self.assertFalse(sequence["feature_mask"][0, 2])
        self.assertTrue(sequence["feature_mask"][:, 3].all())
        self.assertTrue(sequence["stroke_boundary"][0])

    def test_participant_split_is_grouped(self):
        participants = [f"P{index}" for index in range(7)]
        split = assign_participant_splits(participants, seed=7)
        self.assertEqual(set(split), set(participants))
        self.assertEqual(set(split.values()), {"train", "val", "test"})
        again = assign_participant_splits(participants, seed=7)
        self.assertEqual(split, again)

    def test_manifest_builds_rows_and_propagates_session_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, participant, excluded in [
                ("session-a", "P1", False),
                ("session-b", "P2", False),
                ("session-c", "P3", True),
            ]:
                (root / f"{name}.json").write_text(
                    json.dumps(synthetic_session(name, participant, excluded=excluded)),
                    encoding="utf-8",
                )
            labels_path = root / "labels.csv"
            with labels_path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    ["session_id", "emotion", "label_source", "confidence", "annotator", "notes"]
                )
                writer.writerow(["session-a", "anxiety", "manual", "0.9", "A01", ""])
                writer.writerow(["session-b", "", "", "", "", "unlabeled"])
            labels = load_labels(labels_path)
            rows = build_manifest_rows(root, json_files(root), labels)
            self.assertEqual(len(rows), 2)  # excluded_test_record is filtered
            by_session = {row["session_id"]: row for row in rows}
            self.assertEqual(by_session["session-a"]["emotion"], "anxiety")
            self.assertEqual(by_session["session-a"]["label_source"], "manual")
            self.assertEqual(by_session["session-b"]["emotion"], "")
            self.assertEqual(by_session["session-a"]["image_bytes_estimate"], 3)
            summary = manifest_summary(rows)
            self.assertEqual(summary["rows"], 2)
            self.assertEqual(summary["participants"], 2)
            self.assertEqual(summary["labeled_rows"], 1)

    def test_unknown_label_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labels.csv"
            path.write_text("session_id,emotion\nsession-a,not-a-real-emotion\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_labels(path)

    def test_image_estimate(self):
        present, size = image_estimate({"image": {"dataUrl": "data:image/png;base64,AAAA"}})
        self.assertTrue(present)
        self.assertEqual(size, 3)
        self.assertEqual(image_estimate({}), (False, 0))


if __name__ == "__main__":
    unittest.main()
