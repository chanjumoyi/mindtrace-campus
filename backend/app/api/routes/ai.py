from __future__ import annotations

from fastapi import APIRouter

from ...schemas import ChatRequest, ChatResponse


router = APIRouter()
DISCLAIMER = "本平台提供心理健康教育和日常支持，不构成医学诊断，也不替代专业咨询或治疗。"
CRISIS_TERMS = ("自杀", "不想活", "结束生命", "伤害自己", "伤害别人")


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    message = payload.message.strip()
    if any(term in message for term in CRISIS_TERMS):
        return ChatResponse(
            reply="我很重视你刚才表达的危险信号。请先离开可能造成伤害的物品，联系可信任的人陪伴你，并立即联系学校心理中心、当地急救或报警服务。",
            risk_level="urgent_review",
            disclaimer=DISCLAIMER,
        )
    return ChatResponse(
        reply="谢谢你愿意说出来。你可以再描述一下，这件事最近最让你难受的部分是什么？我们可以一起把感受和可行动的一小步理清。",
        risk_level="routine",
        disclaimer=DISCLAIMER,
    )
