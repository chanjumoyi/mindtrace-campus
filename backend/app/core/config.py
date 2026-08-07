from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "心迹AI")
    api_prefix: str = "/api/v1"
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://mindline:mindline_dev_password@mysql:3306/mindline?charset=utf8mb4",
    )
    llm_mode: str = os.getenv("LLM_MODE", "mock")
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    )


settings = Settings()
