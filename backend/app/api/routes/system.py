from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

MODULES: list[dict[str, str]] = [
    {"code": "ai-companion", "name": "AI 对话陪伴", "stage": "mvp"},
    {"code": "journal", "name": "电子手账与情绪记录", "stage": "mvp"},
    {"code": "handwriting", "name": "笔迹行为分析", "stage": "research"},
    {"code": "htp", "name": "房树人辅助观察", "stage": "research"},
    {"code": "sandplay", "name": "AI 辅助沙盘", "stage": "research"},
    {"code": "wellness", "name": "冥想与心理科普", "stage": "mvp"},
]


@router.get("/modules")
def modules() -> list[dict[str, str]]:
    return MODULES
