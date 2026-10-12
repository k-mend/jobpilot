"""Remotive public API connector. https://remotive.com/api/remote-jobs"""
from __future__ import annotations

from typing import List

from app.models.schemas import RawJob, SearchQuery
from app.sources.base import JobSource

API = "https://remotive.com/api/remote-jobs"


class RemotiveSource(JobSource):
    name = "remotive"

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        params = {}
        if query.keywords:
            params["search"] = " ".join(query.keywords)
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(API, params=params)
            resp.raise_for_status()
            data = resp.json()
        for item in data.get("jobs", []):
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    location=item.get("candidate_required_location", "") or "Remote",
                    remote=True,
                    url=item.get("url", ""),
                    description=item.get("description", ""),
                    tags=item.get("tags", []) or [],
                    posted_at=item.get("publication_date"),
                )
            )
        return jobs
