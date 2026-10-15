"""Auth UI routes: signup, login, logout, account, password reset, admin."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import Application, CVDocument, SavedSearch, User
from app.services import auth as auth_service
from app.services import notify as notify_service

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


# --- account: change password (logged in) ------------------------------------------

@router.get("/account", response_class=HTMLResponse)
def account_page(request: Request,
                 user: Optional[User] = Depends(auth_service.get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return _templates().TemplateResponse(
        "account.html", {"request": request, "current_user": user, "message": None,
                         "error": None}
    )


@router.post("/account/password", response_class=HTMLResponse)
def change_password(request: Request, current_password: str = Form(...),
                    new_password: str = Form(...),
                    user: Optional[User] = Depends(auth_service.get_current_user),
                    session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    ctx = {"request": request, "current_user": user, "message": None, "error": None}
    if len(new_password) < 8:
        ctx["error"] = "New password must be at least 8 characters."
    elif not auth_service.change_password(session, user, current_password, new_password):
        ctx["error"] = "Your current password is incorrect."
    else:
        ctx["message"] = "Password updated."
    return _templates().TemplateResponse("account.html", ctx)


# --- forgot / reset password (no login) --------------------------------------------

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_page(request: Request):
    return _templates().TemplateResponse(
        "forgot.html", {"request": request, "message": None}
    )


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot(request: Request, email: str = Form(...),
           session: Session = Depends(get_session)):
    result = auth_service.create_reset_token(session, email)
    if result:
        user, raw_token = result
        reset_url = (
            f"{get_settings().base_url}/reset-password"
            f"?email={user.email}&token={raw_token}"
        )
        notify_service.send_reset_email(user.email, reset_url)
    # Always show the same message (don't reveal whether an account exists).
    return _templates().TemplateResponse(
        "forgot.html",
        {"request": request,
         "message": "If that email has an account, a reset link has been sent."},
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_page(request: Request, email: str = "", token: str = ""):
    return _templates().TemplateResponse(
        "reset.html",
        {"request": request, "email": email, "token": token, "error": None},
    )


@router.post("/reset-password", response_class=HTMLResponse)
def reset(request: Request, email: str = Form(...), token: str = Form(...),
          new_password: str = Form(...), session: Session = Depends(get_session)):
    if len(new_password) < 8:
        return _templates().TemplateResponse(
            "reset.html",
            {"request": request, "email": email, "token": token,
             "error": "Password must be at least 8 characters."},
        )
    ok = auth_service.reset_password_with_token(session, email, token, new_password)
    if not ok:
        return _templates().TemplateResponse(
            "reset.html",
            {"request": request, "email": email, "token": token,
             "error": "Invalid or expired reset link. Request a new one."},
        )
    return RedirectResponse(url="/login", status_code=303)


# --- admin console -----------------------------------------------------------------

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request,
               user: Optional[User] = Depends(auth_service.get_current_user),
               session: Session = Depends(get_session)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if not auth_service.is_admin_user(user):
        return _templates().TemplateResponse(
            "admin.html", {"request": request, "current_user": user, "users": None}
        )
    rows = []
    for u in session.exec(select(User).order_by(User.created_at.desc())).all():
        app_count = len(session.exec(
            select(Application).where(Application.user_id == u.id)
        ).all())
        rows.append({
            "id": u.id, "email": u.email, "name": u.name,
            "is_admin": u.is_admin, "is_disabled": u.is_disabled,
            "created_at": u.created_at, "applications": app_count,
        })
    return _templates().TemplateResponse(
        "admin.html", {"request": request, "current_user": user, "users": rows}
    )


@router.post("/admin/users/{user_id}/revoke")
def admin_revoke(user_id: int,
                 user: Optional[User] = Depends(auth_service.get_current_user),
                 session: Session = Depends(get_session)):
    if not auth_service.is_admin_user(user):
        return RedirectResponse(url="/login", status_code=303)
    target = session.get(User, user_id)
    if target and target.id != user.id:  # can't revoke yourself
        target.is_disabled = not target.is_disabled  # toggle
        session.add(target)
        session.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/admin/users/{user_id}/delete")
def admin_delete(user_id: int,
                 user: Optional[User] = Depends(auth_service.get_current_user),
                 session: Session = Depends(get_session)):
    if not auth_service.is_admin_user(user):
        return RedirectResponse(url="/login", status_code=303)
    target = session.get(User, user_id)
    if target and target.id != user.id:  # can't delete yourself
        # Remove the user's data first (no cascade on SQLite/SQLModel by default).
        for app in session.exec(
            select(Application).where(Application.user_id == user_id)
        ).all():
            session.delete(app)
        for doc in session.exec(
            select(CVDocument).where(CVDocument.user_id == user_id)
        ).all():
            session.delete(doc)
        for s in session.exec(
            select(SavedSearch).where(SavedSearch.user_id == user_id)
        ).all():
            session.delete(s)
        session.delete(target)
        session.commit()
    return RedirectResponse(url="/admin", status_code=303)
