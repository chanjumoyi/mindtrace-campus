from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MoodCreate(BaseModel):
    mood: int = Field(ge=1, le=5)
    stress: int = Field(ge=1, le=5)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    note: str | None = Field(default=None, max_length=1000)


class MoodRead(MoodCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class JournalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=10000)
    emotion: str | None = Field(default=None, max_length=40)


class JournalRead(JournalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    risk_level: str
    disclaimer: str
