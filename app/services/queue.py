"""Scan orchestration and the multi-user application queue/workflow.

A scan: for a query, fetch from all sources, dedupe, rank against query + CV profile,
persist Job rows and `matched` Application rows for the user, then optionally tailor the
top N (CV + cover letter) moving them to `tailored`.

Application lifecycle: matched -> tailored -> ready -> submitted -> archived.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.models import Application, CVDocument, Job, SavedSearch, User
from app.models.schemas import CVProfile, RawJob, SearchQuery
from app.services import cv as cv_service
from app.services import matching
from app.sources.registry import build_sources

VALID_STATUSES = ["matched", "tailored", "ready", "submitted", "archived"]
_NEXT = {
    "matched": "tailored",
    "tailored": "ready",
    "ready": "submitted",
    "submitted": "archived",
}


# --- fetching ----------------------------------------------------------------------

def fetch_all(query: SearchQuery, settings: Optional[Settings] = None) -> List[RawJob]:
    """Fetch from every enabled source, tolerating individual source failures."""
    settings = settings or get_settings()
    results: List[RawJob] = []
    seen = set()
    for source in build_sources(settings):
        try:
            for job in source.fetch(query):
                key = (job.source.split(":")[0], job.external_id) if job.external_id \
                    else (job.source, job.url)
                if key in seen:
                    continue
                seen.add(key)
                results.append(job)
        except Exception as exc:  # one bad source shouldn't kill the scan
            print(f"[scan] source {source.name} failed: {exc}")
    return results


def search(
    query_text: str,
    profile: Optional[CVProfile] = None,
    settings: Optional[Settings] = None,
):
    """Stateless search used by the UI: returns ranked (RawJob, score) pairs."""
    query = matching.parse_query(query_text)
    jobs = fetch_all(query, settings)
    return matching.rank_jobs(jobs, query, profile)


# --- persistence helpers -----------------------------------------------------------

def _upsert_job(session: Session, raw: RawJob) -> Job:
    stmt = select(Job).where(
        Job.source == raw.source, Job.external_id == raw.external_id
    )
    existing = session.exec(stmt).first()
    if existing:
        return existing
    job = Job(
        source=raw.source,
        external_id=raw.external_id,
        title=raw.title,
        company=raw.company,
        location=raw.location,
        remote=raw.remote,
        url=raw.url,
        description=raw.description,
        tags=",".join(raw.tags),
        posted_at=raw.posted_at,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _get_profile_for_user(session: Session, user_id: int) -> Optional[CVProfile]:
    stmt = (
        select(CVDocument)
        .where(CVDocument.user_id == user_id)
        .order_by(CVDocument.created_at.desc())
    )
    doc = session.exec(stmt).first()
    if not doc:
        return None
    return cv_service.profile_from_json(doc.profile_json, doc.raw_text)


# --- the scan ----------------------------------------------------------------------

def run_scan_for_search(
    session: Session,
    saved: SavedSearch,
    settings: Optional[Settings] = None,
    tailor: bool = True,
) -> List[dict]:
    """Run one saved search for its owner. Returns a digest list of new matches."""
    settings = settings or get_settings()
    profile = _get_profile_for_user(session, saved.user_id)
    query = matching.parse_query(saved.description)
    raw_jobs = fetch_all(query, settings)
    ranked = matching.rank_jobs(raw_jobs, query, profile)[: settings.scan_max_results]

    digest: List[dict] = []
    tailored_count = 0
    for raw, score in ranked:
        if score <= 0:
            continue
        job = _upsert_job(session, raw)

        # Skip if this user already has an application for this job.
        existing = session.exec(
            select(Application).where(
                Application.user_id == saved.user_id,
                Application.job_id == job.id,
            )
        ).first()
        if existing:
            continue

        app = Application(
            user_id=saved.user_id,
            job_id=job.id,
            status="matched",
            score=score,
        )

        if tailor and profile and tailored_count < settings.tailor_top_n:
            app.tailored_cv = cv_service.tailor_cv(profile, raw)
            app.cover_letter = cv_service.generate_cover_letter(profile, raw)
            app.status = "tailored"
            tailored_count += 1

        session.add(app)
        session.commit()
        digest.append(
            {
                "title": job.title,
                "company": job.company,
                "url": job.url,
                "score": score,
                "status": app.status,
            }
        )
    return digest


def run_all_active_scans(
    session: Session, settings: Optional[Settings] = None
) -> dict:
    """Run every active saved search for every user. Used by the CLI / Action."""
    settings = settings or get_settings()
    searches = session.exec(select(SavedSearch).where(SavedSearch.active == True)).all()  # noqa: E712
    summary = {}
    for saved in searches:
        digest = run_scan_for_search(session, saved, settings)
        summary.setdefault(saved.user_id, []).extend(digest)
    return summary


# --- workflow transitions ----------------------------------------------------------

def advance(session: Session, application_id: int) -> Optional[Application]:
    app = session.get(Application, application_id)
    if not app:
        return None
    nxt = _NEXT.get(app.status)
    if nxt:
        app.status = nxt
        app.updated_at = datetime.utcnow()
        session.add(app)
        session.commit()
        session.refresh(app)
    return app


def set_status(
    session: Session, application_id: int, status: str
) -> Optional[Application]:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    app = session.get(Application, application_id)
    if not app:
        return None
    app.status = status
    app.updated_at = datetime.utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def tailor_application(session: Session, application_id: int) -> Optional[Application]:
    """(Re)generate tailored CV + cover letter for a single queued application."""
    app = session.get(Application, application_id)
    if not app:
        return None
    job = session.get(Job, app.job_id)
    profile = _get_profile_for_user(session, app.user_id)
    if not job or not profile:
        return app
    raw = RawJob(
        source=job.source,
        external_id=job.external_id,
        title=job.title,
        company=job.company,
        location=job.location,
        remote=job.remote,
        url=job.url,
        description=job.description,
        tags=job.tags.split(",") if job.tags else [],
    )
    app.tailored_cv = cv_service.tailor_cv(profile, raw)
    app.cover_letter = cv_service.generate_cover_letter(profile, raw)
    if app.status == "matched":
        app.status = "tailored"
    app.updated_at = datetime.utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


# --- user helpers ------------------------------------------------------------------

def get_or_create_user(session: Session, email: str, name: str = "") -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        return user
    user = User(email=email, name=name)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
