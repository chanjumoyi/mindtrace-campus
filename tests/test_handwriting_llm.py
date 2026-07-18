from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "local" / "ai-lab" / "handwriting" / "service"
sys.path.insert(0, str(SERVICE))

from llm import HandwritingLlmExplainer, LlmConfig  # noqa: E402


class HandwritingLlmTest(unittest.TestCase):
    def test_mock_never_requires_a_secret(self) -> None:
        explainer = HandwritingLlmExplainer(LlmConfig("mock", "", "", "", 1))
        result = explainer.explain({"observations": [{"description": "记录包含 56 个笔划。"}]})
        self.assertEqual(result["status"], "MOCK")
        self.assertEqual(result["provider"], "mock")
        self.assertEqual(len(result["explorationQuestions"]), 2)

    def test_unconfigured_qwen_degrades_safely(self) -> None:
        explainer = HandwritingLlmExplainer(LlmConfig("qwen", "", "https://example.invalid/v1", "qwen2.5-7b-instruct", 1))
        result = explainer.explain({"observations": []})
        self.assertEqual(result["status"], "DEGRADED")
        self.assertEqual(result["provider"], "mock")
        self.assertIn("未配置", result["degradationNote"])


if __name__ == "__main__":
    unittest.main()
