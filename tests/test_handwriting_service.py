from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "local" / "ai-lab" / "handwriting" / "service"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(SCRIPTS))

from analyzer import TraceValidationError, analyse_trace  # noqa: E402
from inspect_handwriting_trace import self_test_payload  # noqa: E402


class HandwritingServiceTest(unittest.TestCase):
    def test_synthetic_trace_returns_contract_fields(self) -> None:
        result = analyse_trace(self_test_payload(), "req-test")
        self.assertEqual(result["requestId"], "req-test")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["writingContent"], self_test_payload()["task"]["promptText"])
        self.assertGreaterEqual(result["dataQuality"], 0.6)
        self.assertEqual(len(result["observations"]), 4)
        self.assertIn("stateScores", result)
        self.assertIn("citations", result)
        self.assertIn("features", result)

    def test_invalid_trace_is_rejected(self) -> None:
        with self.assertRaises(TraceValidationError):
            analyse_trace({"points": []})


if __name__ == "__main__":
    unittest.main()
