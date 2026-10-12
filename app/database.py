"""SQLite/SQLModel engine and session helpers."""
from __future__ import annotations

from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

_settings = get_settings()

# check_same_thread=False lets the single SQLite file be used across FastAPI threads.
engine = create_engine(
    _settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False}
    if _settings.database_url.startswith("sqlite")
    else {},
)


def init_db() -> None:
    """Create tables. Import models first so they register with SQLModel.metadata."""
    import app.models  # noqa: F401  (side-effect: registers tables)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
