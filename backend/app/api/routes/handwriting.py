from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...services.handwriting.analyzer import TraceValidationError, analyse_trace
from ...services.handwriting.llm import HandwritingLlmExplainer

router = APIRouter()
explainer = HandwritingLlmExplainer()


@router.post("/analyze")
def analyze_handwriting(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = analyse_trace(payload.get("trace", payload), payload.get("requestId"))
    except TraceValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if payload.get("includeLlm", True):
        result["llmExplanation"] = explainer.explain(result)
    return result
