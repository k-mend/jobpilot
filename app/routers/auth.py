"""Auth UI routes: signup, login, logout."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from app.database import get_session
from app.services import auth as auth_service

router = APIRouter(tags=["auth"])


def _templates():
    from app.main import templates

    return templates


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return _templates().TemplateResponse(
        "signup.html", {"request": request, "error": None}
    )


@router.post("/signup", response_class=HTMLResponse)
def signup(request: Request, email: str = Form(...), password: str = Form(...),
           name: str = Form(""), session: Session = Depends(get_session)):
    if len(password) < 8:
        return _templates().TemplateResponse(
            "signup.html",
            {"request": request, "error": "Password must be at least 8 characters."},
        )
    try:
        user = auth_service.create_user(session, email, password, name)
    except ValueError as exc:
        return _templates().TemplateResponse(
            "signup.html", {"request": request, "error": str(exc)}
        )
    resp = RedirectResponse(url="/queue", status_code=303)
    _set_cookie(resp, user.id)
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return _templates().TemplateResponse(
        "login.html", {"request": request, "error": None}
    )


@router.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...),
          session: Session = Depends(get_session)):
    user = auth_service.authenticate(session, email, password)
    if not user:
        return _templates().TemplateResponse(
            "login.html",
            {"request": request, "error": "Wrong email or password."},
        )
    resp = RedirectResponse(url="/queue", status_code=303)
    _set_cookie(resp, user.id)
    return resp


@router.get("/logout")
@router.post("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie(auth_service.COOKIE_NAME)
    return resp


def _set_cookie(resp: RedirectResponse, user_id: int) -> None:
    token = auth_service.make_session_token(user_id)
    resp.set_cookie(
        auth_service.COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True,
        samesite="lax",
    )
