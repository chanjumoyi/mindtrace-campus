from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ...schemas import ChatRequest, ChatResponse
from ...services.chat import chat_service

router = APIRouter()


@router.get("/health", tags=["ai"])
def ai_health() -> dict[str, Any]:
    """Expose whether a real model is configured, so LLM_MODE is observable."""
    return chat_service.health()


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return ChatResponse(**chat_service.reply(payload.message).as_dict())
