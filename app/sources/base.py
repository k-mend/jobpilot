"""Base interface for job sources. Each connector returns normalized RawJob objects."""
from __future__ import annotations

from typing import List

import httpx

from app.models.schemas import RawJob, SearchQuery

USER_AGENT = "JobPilot/0.1 (+https://github.com/) polite-bot"
TIMEOUT = httpx.Timeout(20.0)


class JobSource:
    """Subclasses implement fetch(). name is a stable identifier."""

    name: str = "base"

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        raise NotImplementedError

    @staticmethod
    def _client() -> httpx.Client:
        return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)

    @staticmethod
    def _matches(query: SearchQuery, *text_parts: str) -> bool:
        """Lightweight keyword gate applied client-side when the API lacks search."""
        if not query.keywords:
            return True
        haystack = " ".join(p.lower() for p in text_parts if p)
        return any(kw.lower() in haystack for kw in query.keywords)
