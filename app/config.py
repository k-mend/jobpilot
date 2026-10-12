"""Application settings, driven by environment variables (.env).

Everything has a free, working default. An LLM key is optional.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (optional). No key => free template fallback.
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"

    # Database
    database_url: str = "sqlite:///jobpilot.db"

    # Custom company boards (comma-separated)
    greenhouse_boards: str = ""
    lever_boards: str = ""
    ashby_boards: str = ""

    # Scan behavior
    scan_max_results: int = 50
    tailor_top_n: int = 5

    # App
    app_secret: str = "change-me"

    def board_list(self, raw: str) -> List[str]:
        return [b.strip() for b in raw.split(",") if b.strip()]

    @property
    def greenhouse_board_list(self) -> List[str]:
        return self.board_list(self.greenhouse_boards)

    @property
    def lever_board_list(self) -> List[str]:
        return self.board_list(self.lever_boards)

    @property
    def ashby_board_list(self) -> List[str]:
        return self.board_list(self.ashby_boards)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
