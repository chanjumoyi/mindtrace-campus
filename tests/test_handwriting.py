from __future__ import annotations

import pytest

from backend.app.services.handwriting.analyzer import TraceValidationError, analyse_trace
from backend.app.services.handwriting.llm import HandwritingLlmExplainer, LlmConfig


def synthetic_trace() -> dict:
    points = []
    sequence = 0
    for stroke_id in range(1, 4):
        for offset in range(8):
            sequence += 1
            points.append(
                {
                    "strokeId": stroke_id,
                    "sequence": sequence,
                    "phase": "down" if offset == 0 else "up" if offset == 7 else "move",
                    "pointerType": "pen",
                    "elapsedMs": sequence * 12,
                    "xNorm": 0.1 * stroke_id + offset * 0.01,
                    "yNorm": 0.15 * stroke_id + offset * 0.01,
                    "pressure": 0.2 + offset * 0.05,
                    "tiltX": 5 + offset,
                    "tiltY": 2 + offset,
                }
            )
    return {
        "schemaVersion": "1.0.0",
        "sessionId": "synthetic",
        "participantId": "synthetic",
        "task": {"type": "copy_text", "promptText": "steady practice"},
        "points": points,
    }


def test_synthetic_trace_returns_observations() -> None:
    result = analyse_trace(synthetic_trace(), "req-test")
    assert result["requestId"] == "req-test"
    assert result["status"] == "SUCCESS"
    assert len(result["observations"]) == 4
    assert result["limitations"]


def test_invalid_trace_is_rejected() -> None:
    with pytest.raises(TraceValidationError):
        analyse_trace({"points": []})


def test_llm_mock_never_requires_secret() -> None:
    explainer = HandwritingLlmExplainer(LlmConfig("mock", "", "", "", 1))
    result = explainer.explain({"observations": [{"description": "记录包含 56 个笔划。"}]})
    assert result["status"] == "MOCK"
    assert len(result["explorationQuestions"]) == 2
