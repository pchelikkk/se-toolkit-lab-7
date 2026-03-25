from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_ENV_FILE = Path(__file__).resolve().parents[1] / ".env.bot.secret"


class Settings(BaseSettings):
    bot_token: str | None = None
    lms_api_base_url: str = "http://localhost:42002"
    lms_api_key: str = "2007"
    llm_api_model: str = "qwen3-coder-flash"
    llm_api_key: str = "2007"
    llm_api_base_url: str = "http://localhost:42005/v1"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


def get_settings() -> Settings:
    return Settings()
