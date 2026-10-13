"""Database engine and session helpers.

Supports two backends from one DATABASE_URL:
  - SQLite  (default; great for local dev and tests): sqlite:///jobpilot.db
  - Postgres/Neon (durable production storage):        postgresql://...

Neon gives a URL like:
    postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
We normalize it to use the psycopg (v3) driver and keep a small, pre-ping'd pool so
idle Neon connections that get dropped are transparently recycled.
"""
from __future__ import annotations

from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_settings = get_settings()


def _normalize_url(url: str) -> str:
    """Make common Postgres URL shapes work with the psycopg v3 driver."""
    if url.startswith("postgres://"):
        # Some providers emit the legacy scheme; SQLAlchemy wants postgresql://
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize_url(_settings.database_url)
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # Postgres/Neon: pre_ping avoids "server closed the connection" on idle;
    # pool_recycle keeps connections fresh under Neon's idle timeouts.
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=5,
    )


def init_db() -> None:
    """Create tables. Import models first so they register with SQLModel.metadata."""
    import app.models  # noqa: F401  (side-effect: registers tables)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
