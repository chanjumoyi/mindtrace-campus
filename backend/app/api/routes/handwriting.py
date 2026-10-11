from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...services.handwriting.analyzer import (
    BASELINE_PREDICTOR,
    TraceValidationError,
    analyse_trace,
)
from ...services.handwriting.llm import HandwritingLlmExplainer

router = APIRouter()
explainer = HandwritingLlmExplainer()


@router.get("/health", tags=["handwriting"])
def handwriting_health() -> dict[str, Any]:
    """Expose the configured LLM mode and whether the research model artifact is present."""
    return {"llm": explainer.health(), "baselineModel": BASELINE_PREDICTOR.health()}


@router.post("/analyze")
def analyze_handwriting(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = analyse_trace(payload.get("trace", payload), payload.get("requestId"))
    except TraceValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if payload.get("includeLlm", True):
        result["llmExplanation"] = explainer.explain(result)
    return result
