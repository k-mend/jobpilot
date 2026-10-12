"""Arbeitnow public job board API. https://www.arbeitnow.com/api/job-board-api"""
from __future__ import annotations

from typing import List

from app.models.schemas import RawJob, SearchQuery
from app.sources.base import JobSource

API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowSource(JobSource):
    name = "arbeitnow"

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(API)
            resp.raise_for_status()
            data = resp.json()
        for item in data.get("data", []):
            title = item.get("title", "")
            desc = item.get("description", "")
            tags = item.get("tags", []) or []
            if not self._matches(query, title, desc, " ".join(tags)):
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("slug", "")),
                    title=title,
                    company=item.get("company_name", ""),
                    location=item.get("location", ""),
                    remote=bool(item.get("remote", False)),
                    url=item.get("url", ""),
                    description=desc,
                    tags=tags,
                    posted_at=str(item.get("created_at", "")),
                )
            )
        return jobs
