from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./mindline-test.db")

from fastapi.testclient import TestClient

from backend.app.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_crisis_language_uses_urgent_path() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/ai/chat", json={"message": "我不想活了"})
    assert response.status_code == 200
    assert response.json()["risk_level"] == "urgent_review"


def test_modules_cover_report_scope() -> None:
    with TestClient(app) as client:
        codes = {item["code"] for item in client.get("/api/v1/modules").json()}
    assert {"ai-companion", "journal", "handwriting", "htp", "sandplay", "wellness"} <= codes
