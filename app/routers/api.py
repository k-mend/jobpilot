"""JSON API endpoints under /api."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_session
from app.models import Application, CVDocument, Job, SavedSearch, User
from app.services import cv as cv_service
from app.services import queue as queue_service

router = APIRouter(prefix="/api", tags=["api"])


# --- schemas ----------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    user_email: Optional[str] = None


class JobResult(BaseModel):
    source: str
    title: str
    company: str
    location: str
    remote: bool
    url: str
    score: float


class SavedSearchRequest(BaseModel):
    user_email: str
    description: str
    active: bool = True


class StatusRequest(BaseModel):
    status: str


# --- search -----------------------------------------------------------------------

@router.post("/search", response_model=List[JobResult])
def search(req: SearchRequest, session: Session = Depends(get_session)):
    profile = None
    if req.user_email:
        user = session.exec(select(User).where(User.email == req.user_email)).first()
        if user:
            profile = queue_service._get_profile_for_user(session, user.id)
    ranked = queue_service.search(req.query, profile)
    return [
        JobResult(
            source=j.source,
            title=j.title,
            company=j.company,
            location=j.location,
            remote=j.remote,
            url=j.url,
            score=score,
        )
        for j, score in ranked
        if score > 0
    ]


# --- users & CV -------------------------------------------------------------------

@router.post("/users")
def create_user(email: str = Form(...), name: str = Form(""),
                session: Session = Depends(get_session)):
    user = queue_service.get_or_create_user(session, email, name)
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/users/{user_id}/cv")
async def upload_cv(user_id: int, file: UploadFile = File(...),
                    session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    content = await file.read()
    profile = cv_service.parse_cv(file.filename, content)
    doc = CVDocument(
        user_id=user_id,
        filename=file.filename,
        raw_text=profile.raw_text,
        profile_json=cv_service.profile_to_json(profile),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return {
        "cv_id": doc.id,
        "skills": profile.skills,
        "titles": profile.titles,
        "years_experience": profile.years_experience,
    }


# --- saved searches ---------------------------------------------------------------

@router.post("/saved-searches")
def create_saved_search(req: SavedSearchRequest,
                        session: Session = Depends(get_session)):
    user = queue_service.get_or_create_user(session, req.user_email)
    saved = SavedSearch(user_id=user.id, description=req.description, active=req.active)
    session.add(saved)
    session.commit()
    session.refresh(saved)
    return {"id": saved.id, "description": saved.description, "active": saved.active}


@router.post("/saved-searches/{search_id}/scan")
def scan_saved_search(search_id: int, session: Session = Depends(get_session)):
    saved = session.get(SavedSearch, search_id)
    if not saved:
        raise HTTPException(404, "saved search not found")
    digest = queue_service.run_scan_for_search(session, saved)
    return {"matches": digest}


# --- applications / queue ---------------------------------------------------------

@router.get("/users/{user_id}/applications")
def list_applications(user_id: int, status: Optional[str] = None,
                      session: Session = Depends(get_session)):
    stmt = select(Application).where(Application.user_id == user_id)
    if status:
        stmt = stmt.where(Application.status == status)
    stmt = stmt.order_by(Application.score.desc())
    apps = session.exec(stmt).all()
    out = []
    for a in apps:
        job = session.get(Job, a.job_id)
        out.append(
            {
                "id": a.id,
                "status": a.status,
                "score": a.score,
                "title": job.title if job else "",
                "company": job.company if job else "",
                "url": job.url if job else "",
            }
        )
    return out


@router.post("/applications/{application_id}/tailor")
def tailor(application_id: int, session: Session = Depends(get_session)):
    app = queue_service.tailor_application(session, application_id)
    if not app:
        raise HTTPException(404, "application not found")
    return {"id": app.id, "status": app.status, "tailored_cv": app.tailored_cv,
            "cover_letter": app.cover_letter}


@router.post("/applications/{application_id}/advance")
def advance(application_id: int, session: Session = Depends(get_session)):
    app = queue_service.advance(session, application_id)
    if not app:
        raise HTTPException(404, "application not found")
    return {"id": app.id, "status": app.status}


@router.post("/applications/{application_id}/status")
def set_status(application_id: int, req: StatusRequest,
               session: Session = Depends(get_session)):
    try:
        app = queue_service.set_status(session, application_id, req.status)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not app:
        raise HTTPException(404, "application not found")
    return {"id": app.id, "status": app.status}


@router.get("/health")
def health():
    return {"status": "ok"}
