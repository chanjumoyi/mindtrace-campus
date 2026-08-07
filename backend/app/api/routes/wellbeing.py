from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import JournalEntry, MoodEntry
from ...schemas import JournalCreate, JournalRead, MoodCreate, MoodRead


router = APIRouter()


@router.get("/moods", response_model=list[MoodRead])
def list_moods(db: Session = Depends(get_db)) -> list[MoodEntry]:
    return list(db.scalars(select(MoodEntry).order_by(MoodEntry.created_at.desc()).limit(30)))


@router.post("/moods", response_model=MoodRead, status_code=status.HTTP_201_CREATED)
def create_mood(payload: MoodCreate, db: Session = Depends(get_db)) -> MoodEntry:
    entry = MoodEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/journals", response_model=list[JournalRead])
def list_journals(db: Session = Depends(get_db)) -> list[JournalEntry]:
    return list(db.scalars(select(JournalEntry).order_by(JournalEntry.created_at.desc()).limit(50)))


@router.post("/journals", response_model=JournalRead, status_code=status.HTTP_201_CREATED)
def create_journal(payload: JournalCreate, db: Session = Depends(get_db)) -> JournalEntry:
    entry = JournalEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/resources")
def wellness_resources() -> list[dict[str, str]]:
    return [
        {"type": "breathing", "title": "一分钟呼吸练习", "duration": "1 分钟"},
        {"type": "meditation", "title": "专注当下冥想", "duration": "5 分钟"},
        {"type": "science", "title": "认识压力反应", "duration": "3 分钟"},
    ]
