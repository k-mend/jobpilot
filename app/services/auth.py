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

from typing import Optional

import bcrypt
from fastapi import Depends, Request
from itsdangerous import BadSignature, URLSafeSerializer
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models import User

COOKIE_NAME = "jobpilot_session"
_MAX_BCRYPT_BYTES = 72  # bcrypt only uses the first 72 bytes of a password


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

def create_user(session: Session, email: str, password: str, name: str = "") -> User:
    """Create a user with a hashed password. Raises ValueError if email exists."""
    email = email.strip().lower()
    existing = session.exec(select(User).where(User.email == email)).first()
    if existing and existing.password_hash:
        raise ValueError("An account with this email already exists.")
    if existing:
        # Upgrade a legacy/CLI user (no password) into a real account.
        existing.password_hash = hash_password(password)
        if name:
            existing.name = name
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    user = User(email=email, name=name, password_hash=hash_password(password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> Optional[User]:
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


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
