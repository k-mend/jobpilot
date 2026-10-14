"""Application settings, driven by environment variables (.env).

Everything has a free, working default. An LLM key is optional.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (optional). No key => free template fallback.
    # Provider is auto-selected: OpenRouter if its key is set, else Gemini.
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"

    # OpenRouter (optional). Has genuinely free models (see docs/LLM_PROVIDERS.md).
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Database
    database_url: str = "sqlite:///jobpilot.db"

    # Custom company boards (comma-separated)
    greenhouse_boards: str = ""
    lever_boards: str = ""
    ashby_boards: str = ""

    # Scan behavior
    scan_max_results: int = 50
    tailor_top_n: int = 5
    scan_min_score: float = 25.0  # ignore weak matches below this (0-100)

    # Email alerts. Two options (see docs/EMAIL_ALERTS.md):
    #   A) Resend  — HTTP API, free tier, no App Password needed (recommended, esp. for
    #      brand-new Google accounts that can't make App Passwords yet).
    #   B) Gmail SMTP — needs 2FA + an App Password.
    resend_api_key: Optional[str] = None
    # The "from" address for Resend. Until you verify your own domain, Resend lets you
    # send from onboarding@resend.dev (great for testing to your own inbox).
    resend_from: str = "JobPilot <onboarding@resend.dev>"

    # Gmail SMTP (alternative to Resend)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None

    # Monthly cleanup / retention (days). Jobs expire ~1 month, so defaults are tuned
    # for that. See docs/RETENTION.md.
    retain_archived_days: int = 90       # applied/closed items kept this long
    retain_stale_matched_days: int = 35  # never-acted-on matches dropped after this
    retain_orphan_job_days: int = 45     # jobs with no application dropped after this

    # App / auth
    app_secret: str = "change-me"  # also signs the session cookie
    base_url: str = "http://127.0.0.1:8000"

    @field_validator("smtp_port", mode="before")
    @classmethod
    def _blank_port_to_default(cls, v):
        # Empty env vars (e.g. SMTP_PORT="") must not crash startup.
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return 587
        return v

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
        return bool(self.openrouter_api_key or self.gemini_api_key)

    @property
    def email_enabled(self) -> bool:
        return bool(
            self.resend_api_key
            or (self.smtp_host and self.smtp_user and self.smtp_password)
        )

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    @property
    def active_provider(self) -> Optional[str]:
        """Which LLM provider will be used, if any. OpenRouter takes priority."""
        if self.openrouter_api_key:
            return "openrouter"
        if self.gemini_api_key:
            return "gemini"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
