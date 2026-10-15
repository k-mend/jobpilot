"""SQLModel database tables.

Tables: User, CVDocument, SavedSearch, Job, Application.
Application lifecycle: matched -> tailored -> ready -> submitted -> archived.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.utcnow()


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str = ""
    # Auth. password_hash is empty for legacy/CLI-created users (cannot log in until set).
    password_hash: str = ""
    is_verified: bool = False
    # Admin can view/revoke/delete users. is_disabled blocks login (revoked by admin).
    is_admin: bool = False
    is_disabled: bool = False
    # Password reset: a hashed token + expiry. Cleared after use.
    reset_token_hash: str = ""
    reset_expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now)


class CVDocument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    filename: str = ""
    raw_text: str = ""
    # JSON-encoded CVProfile (skills, titles, years, summary)
    profile_json: str = "{}"
    created_at: datetime = Field(default_factory=_now)


class SavedSearch(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    description: str = ""  # the natural-language query
    active: bool = True
    created_at: datetime = Field(default_factory=_now)


class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str = Field(index=True)
    external_id: str = Field(index=True)
    title: str = ""
    company: str = ""
    location: str = ""
    remote: bool = False
    url: str = ""
    description: str = ""
    tags: str = ""  # comma-separated
    posted_at: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class Application(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")
    job_id: int = Field(index=True, foreign_key="job.id")
    status: str = Field(default="matched", index=True)
    score: float = 0.0
    tailored_cv: str = ""
    cover_letter: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
