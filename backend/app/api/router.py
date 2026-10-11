from __future__ import annotations

from fastapi import APIRouter

from .routes import ai, handwriting, system, wellbeing

api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(wellbeing.router, prefix="/wellbeing", tags=["wellbeing"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(handwriting.router, prefix="/handwriting", tags=["handwriting"])
