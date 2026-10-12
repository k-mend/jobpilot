"""RemoteOK public API connector. https://remoteok.com/api

The first element of the response is metadata/legal notice, not a job.
"""
from __future__ import annotations

from typing import List

from app.models.schemas import RawJob, SearchQuery
from app.sources.base import JobSource

API = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    name = "remoteok"

    def fetch(self, query: SearchQuery) -> List[RawJob]:
        jobs: List[RawJob] = []
        with self._client() as client:
            resp = client.get(API)
            resp.raise_for_status()
            data = resp.json()
        for item in data:
            if not isinstance(item, dict) or "position" not in item:
                continue  # skip the leading metadata entry
            title = item.get("position", "") or item.get("title", "")
            desc = item.get("description", "")
            if not self._matches(query, title, desc, " ".join(item.get("tags", []) or [])):
                continue
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id", "")),
                    title=title,
                    company=item.get("company", ""),
                    location=item.get("location", "") or "Remote",
                    remote=True,
                    url=item.get("url", ""),
                    description=desc,
                    tags=item.get("tags", []) or [],
                    posted_at=item.get("date"),
                )
            )
        return jobs
