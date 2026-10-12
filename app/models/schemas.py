"""Plain dataclasses shared across services (not persisted directly)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RawJob:
    """Normalized job from any source before it becomes a Job row."""

    source: str
    external_id: str
    title: str
    company: str = ""
    location: str = ""
    remote: bool = False
    url: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    posted_at: Optional[str] = None


@dataclass
class SearchQuery:
    """Structured form of a natural-language job description."""

    raw: str = ""
    keywords: List[str] = field(default_factory=list)
    seniority: Optional[str] = None  # junior | mid | senior | lead
    remote: Optional[bool] = None
    locations: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)


@dataclass
class CVProfile:
    """Structured view of a parsed CV."""

    summary: str = ""
    skills: List[str] = field(default_factory=list)
    titles: List[str] = field(default_factory=list)
    years_experience: Optional[int] = None
    raw_text: str = ""
