from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "local" / "ai-lab" / "handwriting" / "service"
sys.path.insert(0, str(SERVICE))

from baseline import HandwritingBaselinePredictor  # noqa: E402


class HandwritingBaselineTest(unittest.TestCase):
    def test_missing_model_degrades_without_failing_analysis(self) -> None:
        predictor = HandwritingBaselinePredictor(ROOT / "does-not-exist.json")
        result = predictor.predict({})
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["confidenceLevel"], "NONE")

    def test_prediction_is_clamped_and_marked_experimental(self) -> None:
        artifact = {
            "modelVersion": "test-model",
            "sampleCount": 4,
            "participantCount": 2,
            "featureNames": ["point_count"],
            "featureMeans": [10.0],
            "featureScales": [2.0],
            "targets": {
                "stress_level": {"intercept": 3.0, "coefficients": [1.0]},
                "mood_level": {"intercept": 3.0, "coefficients": [-1.0]},
                "sleep_quality": {"intercept": 3.0, "coefficients": [0.0]},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            result = HandwritingBaselinePredictor(path).predict({"counts": {"points": 20}})
        self.assertEqual(result["status"], "EXPERIMENTAL")
        self.assertEqual(result["confidenceLevel"], "LOW")
        self.assertEqual(result["scores"]["stress_level"]["value"], 5.0)
        self.assertEqual(result["scores"]["mood_level"]["value"], 1.0)


if __name__ == "__main__":
    unittest.main()
