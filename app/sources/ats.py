"""Public ATS board connectors: Greenhouse, Lever, Ashby.

Each is keyed by a board token/slug the user supplies (a company's public board).
These endpoints are the companies' own public job listings.
"""
from __future__ import annotations

from typing import List

from app.models.schemas import RawJob, SearchQuery
from app.sources.base import JobSource


class GreenhouseSource(JobSource):
    name = "greenhouse"

    def __init__(self, board: str) -> None:
        self.board = board

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        url = (
            f"https://boards-api.greenhouse.io/v1/boards/{self.board}/jobs"
            "?content=true"
        )
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        for item in data.get("jobs", []):
            title = item.get("title", "")
            desc = item.get("content", "")
            if not self._matches(query, title, desc):
                continue
            loc = (item.get("location") or {}).get("name", "")
            jobs.append(
                RawJob(
                    source=f"{self.name}:{self.board}",
                    external_id=str(item.get("id", "")),
                    title=title,
                    company=self.board,
                    location=loc,
                    remote="remote" in loc.lower(),
                    url=item.get("absolute_url", ""),
                    description=desc,
                    posted_at=item.get("updated_at"),
                )
            )
        return jobs


class LeverSource(JobSource):
    name = "lever"

    def __init__(self, board: str) -> None:
        self.board = board

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        url = f"https://api.lever.co/v0/postings/{self.board}?mode=json"
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        for item in data:
            title = item.get("text", "")
            desc = item.get("descriptionPlain", "") or item.get("description", "")
            if not self._matches(query, title, desc):
                continue
            cats = item.get("categories", {}) or {}
            loc = cats.get("location", "")
            jobs.append(
                RawJob(
                    source=f"{self.name}:{self.board}",
                    external_id=str(item.get("id", "")),
                    title=title,
                    company=self.board,
                    location=loc,
                    remote="remote" in str(loc).lower(),
                    url=item.get("hostedUrl", ""),
                    description=desc,
                    posted_at=str(item.get("createdAt", "")),
                )
            )
        return jobs


class AshbySource(JobSource):
    name = "ashby"

    def __init__(self, board: str) -> None:
        self.board = board

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        url = (
            "https://api.ashbyhq.com/posting-api/job-board/"
            f"{self.board}?includeCompensation=true"
        )
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        for item in data.get("jobs", []):
            title = item.get("title", "")
            desc = item.get("descriptionPlain", "") or item.get("description", "")
            if not self._matches(query, title, desc):
                continue
            loc = item.get("location", "")
            jobs.append(
                RawJob(
                    source=f"{self.name}:{self.board}",
                    external_id=str(item.get("id", "")),
                    title=title,
                    company=self.board,
                    location=loc,
                    remote=bool(item.get("isRemote", False)),
                    url=item.get("jobUrl", ""),
                    description=desc,
                    posted_at=item.get("publishedAt"),
                )
            )
        return jobs
