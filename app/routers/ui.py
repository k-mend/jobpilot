"""Server-rendered UI pages."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Application, CVDocument, Job, User
from app.services import cv as cv_service
from app.services import queue as queue_service

router = APIRouter(tags=["ui"])


def _templates():
    from app.main import templates

    return templates


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return _templates().TemplateResponse(
        "index.html",
        {"request": request, "llm_enabled": get_settings().llm_enabled},
    )


@router.post("/search", response_class=HTMLResponse)
def do_search(request: Request, query: str = Form(...),
              user_email: str = Form(""),
              session: Session = Depends(get_session)):
    profile = None
    if user_email:
        user = session.exec(select(User).where(User.email == user_email)).first()
        if user:
            profile = queue_service._get_profile_for_user(session, user.id)
    ranked = queue_service.search(query, profile)
    results = [
        {
            "title": j.title, "company": j.company, "location": j.location,
            "remote": j.remote, "url": j.url, "score": score, "source": j.source,
        }
        for j, score in ranked if score > 0
    ]
    return _templates().TemplateResponse(
        "results.html",
        {"request": request, "query": query, "results": results,
         "user_email": user_email},
    )


@router.get("/cv", response_class=HTMLResponse)
def cv_page(request: Request):
    return _templates().TemplateResponse("cv.html", {"request": request, "result": None})


@router.post("/cv", response_class=HTMLResponse)
async def cv_upload(request: Request, email: str = Form(...),
                    file: UploadFile = File(...),
                    session: Session = Depends(get_session)):
    user = queue_service.get_or_create_user(session, email)
    content = await file.read()
    profile = cv_service.parse_cv(file.filename, content)
    doc = CVDocument(
        user_id=user.id,
        filename=file.filename,
        raw_text=profile.raw_text,
        profile_json=cv_service.profile_to_json(profile),
    )
    session.add(doc)
    session.commit()
    result = {
        "email": email, "filename": file.filename,
        "skills": profile.skills, "titles": profile.titles,
        "years_experience": profile.years_experience,
    }
    return _templates().TemplateResponse(
        "cv.html", {"request": request, "result": result}
    )


@router.get("/queue", response_class=HTMLResponse)
def queue_page(request: Request, email: Optional[str] = None,
               session: Session = Depends(get_session)):
    applications = []
    if email:
        user = session.exec(select(User).where(User.email == email)).first()
        if user:
            apps = session.exec(
                select(Application)
                .where(Application.user_id == user.id)
                .order_by(Application.score.desc())
            ).all()
            for a in apps:
                job = session.get(Job, a.job_id)
                applications.append({
                    "id": a.id, "status": a.status, "score": a.score,
                    "title": job.title if job else "",
                    "company": job.company if job else "",
                    "url": job.url if job else "",
                    "cover_letter": a.cover_letter,
                })
    return _templates().TemplateResponse(
        "queue.html",
        {"request": request, "email": email or "", "applications": applications,
         "statuses": queue_service.VALID_STATUSES},
    )


@router.post("/queue/{application_id}/status", response_class=HTMLResponse)
def queue_set_status(application_id: int, status: str = Form(...),
                     email: str = Form(""),
                     session: Session = Depends(get_session)):
    try:
        queue_service.set_status(session, application_id, status)
    except ValueError:
        pass
    return RedirectResponse(url=f"/queue?email={email}", status_code=303)


@router.post("/queue/{application_id}/tailor", response_class=HTMLResponse)
def queue_tailor(application_id: int, email: str = Form(""),
                 session: Session = Depends(get_session)):
    queue_service.tailor_application(session, application_id)
    return RedirectResponse(url=f"/queue?email={email}", status_code=303)
