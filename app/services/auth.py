"""Authentication: password hashing + signed session cookies.

Simple email+password auth:
  - passwords hashed with bcrypt (never stored in plaintext),
  - login state carried in a signed, HTTP-only cookie (itsdangerous),
  - a FastAPI dependency resolves the current user from that cookie.

Caveats (documented in docs/AUTH.md):
  - This is lightweight session auth, not OAuth. Good for a small app.
  - The cookie is signed (tamper-proof) but readable; it stores only the user id.
  - APP_SECRET must be set to a strong random value in production, or cookies from a
    previous secret become invalid.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import bcrypt
from fastapi import Depends, Request
from itsdangerous import BadSignature, URLSafeSerializer
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import User

COOKIE_NAME = "jobpilot_session"
_MAX_BCRYPT_BYTES = 72  # bcrypt only uses the first 72 bytes of a password
RESET_TOKEN_TTL_MINUTES = 60


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().app_secret, salt="jobpilot-session")


# --- password hashing --------------------------------------------------------------

def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        pw = password.encode("utf-8")[:_MAX_BCRYPT_BYTES]
        return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- session cookie ----------------------------------------------------------------

def make_session_token(user_id: int) -> str:
    return _serializer().dumps({"uid": user_id})


def read_session_token(token: str) -> Optional[int]:
    try:
        data = _serializer().loads(token)
        return int(data.get("uid"))
    except (BadSignature, ValueError, TypeError, AttributeError):
        return None


# --- user operations ---------------------------------------------------------------

def _should_be_admin(session: Session, email: str) -> bool:
    """Admin if in ADMIN_EMAILS, or if this is the very first account (bootstrap)."""
    email = email.strip().lower()
    if email in get_settings().admin_email_list:
        return True
    # Bootstrap: first user ever becomes admin so there's always an owner.
    any_user = session.exec(select(User)).first()
    return any_user is None


def create_user(session: Session, email: str, password: str, name: str = "") -> User:
    """Create a user with a hashed password. Raises ValueError if email exists."""
    email = email.strip().lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing and existing.password_hash:
        raise ValueError("An account with this email already exists.")
    admin = _should_be_admin(session, email)
    if existing:
        # Upgrade a legacy/CLI user (no password) into a real account.
        existing.password_hash = hash_password(password)
        if name:
            existing.name = name
        if admin:
            existing.is_admin = True
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    user = User(
        email=email, name=name, password_hash=hash_password(password), is_admin=admin
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> Optional[User]:
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or user.is_disabled:
        return None
    if verify_password(password, user.password_hash):
        # Keep admin grant in sync with ADMIN_EMAILS at login time.
        if email in get_settings().admin_email_list and not user.is_admin:
            user.is_admin = True
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    return None


# --- password change + reset -------------------------------------------------------

def change_password(
    session: Session, user: User, current_password: str, new_password: str
) -> bool:
    """Change a logged-in user's password after verifying the current one."""
    if not verify_password(current_password, user.password_hash):
        return False
    user.password_hash = hash_password(new_password)
    session.add(user)
    session.commit()
    return True


def create_reset_token(session: Session, email: str) -> Optional[Tuple[User, str]]:
    """Issue a one-time reset token for the email. Returns (user, raw_token) or None.

    The raw token is emailed to the user; only its hash is stored.
    """
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or user.is_disabled:
        return None
    raw_token = secrets.token_urlsafe(32)
    user.reset_token_hash = hash_password(raw_token)
    user.reset_expires_at = datetime.utcnow() + timedelta(
        minutes=RESET_TOKEN_TTL_MINUTES
    )
    session.add(user)
    session.commit()
    return user, raw_token


def reset_password_with_token(
    session: Session, email: str, token: str, new_password: str
) -> bool:
    """Consume a valid, unexpired reset token and set a new password."""
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not user.reset_token_hash or not user.reset_expires_at:
        return False
    if datetime.utcnow() > user.reset_expires_at:
        return False
    if not verify_password(token, user.reset_token_hash):
        return False
    user.password_hash = hash_password(new_password)
    user.reset_token_hash = ""
    user.reset_expires_at = None
    session.add(user)
    session.commit()
    return True


# --- FastAPI dependencies ----------------------------------------------------------

def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> Optional[User]:
    """Return the logged-in User, or None. Never raises (use for optional auth)."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    uid = read_session_token(token)
    if uid is None:
        return None
    return session.get(User, uid)


def is_admin_user(user: Optional[User]) -> bool:
    return bool(user and user.is_admin and not user.is_disabled)
