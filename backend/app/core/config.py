from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    """Read an int from the environment without letting a bad value crash startup."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "心迹AI")
    api_prefix: str = "/api/v1"
    environment: str = os.getenv("APP_ENV", "development")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://mindline:mindline_dev_password@mysql:3306/mindline?charset=utf8mb4",
    )
    llm_mode: str = os.getenv("LLM_MODE", "mock").strip().lower()
    llm_model: str = os.getenv("LLM_MODEL", "deepseek-chat").strip()
    llm_api_key: str = (os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()
    llm_base_url: str = os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL).strip()
    llm_timeout_seconds: int = _int_env("LLM_TIMEOUT_SECONDS", 20, 1, 120)
    llm_max_attempts: int = _int_env("LLM_MAX_ATTEMPTS", 3, 1, 5)
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    )


settings = Settings()
