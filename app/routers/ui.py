"""Server-rendered UI pages (auth-aware)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Application, CVDocument, Job, SavedSearch, User
from app.services import auth as auth_service
from app.services import cv as cv_service
from app.services import queue as queue_service

router = APIRouter(tags=["ui"])


def _templates():
    from app.main import templates

    return templates


def _ctx(request: Request, user: Optional[User], **extra):
    """Common template context including the logged-in user (for the nav)."""
    base = {"request": request, "current_user": user}
    base.update(extra)
    return base


def _login_redirect():
    return RedirectResponse(url="/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
def home(request: Request, user: Optional[User] = Depends(auth_service.get_current_user)):
    return _templates().TemplateResponse(
        "index.html", _ctx(request, user, llm_enabled=get_settings().llm_enabled)
    )


@router.post("/search", response_class=HTMLResponse)
def do_search(request: Request, query: str = Form(...),
              user: Optional[User] = Depends(auth_service.get_current_user),
              session: Session = Depends(get_session)):
    profile = None
    if user:
        profile = queue_service._get_profile_for_user(session, user.id)
    ranked = queue_service.search(query, profile)
    results = [
        {
            "title": j.title, "company": j.company, "location": j.location,
            "remote": j.remote, "url": j.url, "score": score, "source": j.source,
            "description": j.description, "external_id": j.external_id,
        }
        for j, score in ranked if score > 0
    ]
    return _templates().TemplateResponse(
        "results.html", _ctx(request, user, query=query, results=results,
                             logged_in=bool(user))
    )


# --- CV (requires login) -----------------------------------------------------------

@router.get("/cv", response_class=HTMLResponse)
def cv_page(request: Request,
            user: Optional[User] = Depends(auth_service.get_current_user)):
    if not user:
        return _login_redirect()
    return _templates().TemplateResponse("cv.html", _ctx(request, user, result=None))


@router.post("/cv", response_class=HTMLResponse)
async def cv_upload(request: Request, file: UploadFile = File(...),
                    user: Optional[User] = Depends(auth_service.get_current_user),
                    session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
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
        "filename": file.filename, "skills": profile.skills,
        "titles": profile.titles, "years_experience": profile.years_experience,
    }
    return _templates().TemplateResponse("cv.html", _ctx(request, user, result=result))


# --- saved searches + queue (requires login) ---------------------------------------

@router.get("/queue", response_class=HTMLResponse)
def queue_page(request: Request,
               user: Optional[User] = Depends(auth_service.get_current_user),
               session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    apps = session.exec(
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.score.desc())
    ).all()
    applications = []
    for a in apps:
        job = session.get(Job, a.job_id)
        applications.append({
            "id": a.id, "status": a.status, "score": a.score,
            "title": job.title if job else "",
            "company": job.company if job else "",
            "url": job.url if job else "",
        })
    searches = session.exec(
        select(SavedSearch).where(SavedSearch.user_id == user.id)
    ).all()
    return _templates().TemplateResponse(
        "queue.html",
        _ctx(request, user, applications=applications,
             statuses=queue_service.VALID_STATUSES, searches=searches,
             email_enabled=get_settings().email_enabled),
    )


@router.post("/saved-searches")
def create_saved_search(request: Request, description: str = Form(...),
                        user: Optional[User] = Depends(auth_service.get_current_user),
                        session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    session.add(SavedSearch(user_id=user.id, description=description, active=True))
    session.commit()
    return RedirectResponse(url="/queue", status_code=303)


@router.post("/saved-searches/{search_id}/delete")
def delete_saved_search(search_id: int,
                        user: Optional[User] = Depends(auth_service.get_current_user),
                        session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    s = session.get(SavedSearch, search_id)
    if s and s.user_id == user.id:
        session.delete(s)
        session.commit()
    return RedirectResponse(url="/queue", status_code=303)


@router.post("/queue/{application_id}/status", response_class=HTMLResponse)
def queue_set_status(application_id: int, status: str = Form(...),
                     next: str = Form(""),
                     user: Optional[User] = Depends(auth_service.get_current_user),
                     session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = session.get(Application, application_id)
    if app and app.user_id == user.id:
        try:
            queue_service.set_status(session, application_id, status)
        except ValueError:
            pass
    return RedirectResponse(url=next or "/queue", status_code=303)


@router.post("/queue/{application_id}/tailor", response_class=HTMLResponse)
def queue_tailor(application_id: int, next: str = Form(""),
                 user: Optional[User] = Depends(auth_service.get_current_user),
                 session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = session.get(Application, application_id)
    if app and app.user_id == user.id:
        queue_service.tailor_application(session, application_id)
    return RedirectResponse(url=next or "/queue", status_code=303)


# --- save from search + application detail (requires login) ------------------------

@router.post("/save", response_class=HTMLResponse)
def save_from_results(request: Request,
                      source: str = Form("manual"), title: str = Form(...),
                      company: str = Form(""), location: str = Form(""),
                      remote: str = Form(""), url: str = Form(""),
                      description: str = Form(""), external_id: str = Form(""),
                      score: float = Form(0.0),
                      user: Optional[User] = Depends(auth_service.get_current_user),
                      session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = queue_service.save_job_to_queue(
        session, user.email,
        source=source, title=title, company=company, location=location,
        remote=bool(remote), url=url, description=description,
        external_id=external_id, score=score,
    )
    return RedirectResponse(url=f"/application/{app.id}", status_code=303)


@router.get("/application/{application_id}", response_class=HTMLResponse)
def application_detail(application_id: int, request: Request,
                       user: Optional[User] = Depends(auth_service.get_current_user),
                       session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = session.get(Application, application_id)
    if not app or app.user_id != user.id:
        return _templates().TemplateResponse(
            "application.html", _ctx(request, user, app=None)
        )
    job = session.get(Job, app.job_id)
    data = {
        "id": app.id, "status": app.status, "score": app.score,
        "tailored_cv": app.tailored_cv, "cover_letter": app.cover_letter,
        "title": job.title if job else "", "company": job.company if job else "",
        "location": job.location if job else "", "url": job.url if job else "",
        "description": job.description if job else "",
    }
    return _templates().TemplateResponse(
        "application.html",
        _ctx(request, user, app=data, statuses=queue_service.VALID_STATUSES,
             has_llm=get_settings().llm_enabled),
    )


@router.get("/application/{application_id}/download/cv")
def download_cv(application_id: int,
                user: Optional[User] = Depends(auth_service.get_current_user),
                session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = session.get(Application, application_id)
    if not app or app.user_id != user.id or not app.tailored_cv:
        return PlainTextResponse("No tailored CV yet. Click 'Tailor' first.",
                                 status_code=404)
    return PlainTextResponse(
        app.tailored_cv,
        headers={"Content-Disposition":
                 f'attachment; filename="jobpilot_cv_{application_id}.txt"'},
    )


@router.get("/application/{application_id}/download/cover-letter")
def download_cover(application_id: int,
                   user: Optional[User] = Depends(auth_service.get_current_user),
                   session: Session = Depends(get_session)):
    if not user:
        return _login_redirect()
    app = session.get(Application, application_id)
    if not app or app.user_id != user.id or not app.cover_letter:
        return PlainTextResponse("No cover letter yet. Click 'Tailor' first.",
                                 status_code=404)
    return PlainTextResponse(
        app.cover_letter,
        headers={"Content-Disposition":
                 f'attachment; filename="jobpilot_cover_letter_{application_id}.txt"'},
    )
