import os
import tempfile
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["APP_SECRET"] = "reset-admin-secret"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

init_db()


def _signup(email, password="password123"):
    c = TestClient(app)
    r = c.post("/signup", data={"email": email, "password": password},
               follow_redirects=False)
    assert r.status_code == 303
    return c


# --- change password ---------------------------------------------------------------

def test_change_password_requires_correct_current():
    c = _signup("cp@example.com")
    # wrong current password rejected
    r = c.post("/account/password",
               data={"current_password": "wrong", "new_password": "newpassword1"})
    assert "incorrect" in r.text
    # correct current password works
    r = c.post("/account/password",
               data={"current_password": "password123", "new_password": "newpassword1"})
    assert "updated" in r.text.lower()
    # old password no longer logs in; new one does
    assert auth_service.authenticate(_sess(), "cp@example.com", "password123") is None
    assert auth_service.authenticate(_sess(), "cp@example.com", "newpassword1")


def _sess():
    return Session(engine)


# --- reset token flow --------------------------------------------------------------

def test_reset_token_issue_and_consume():
    _signup("rt@example.com")
    with Session(engine) as s:
        user, raw = auth_service.create_reset_token(s, "rt@example.com")
        assert raw and user.reset_token_hash
    with Session(engine) as s:
        ok = auth_service.reset_password_with_token(
            s, "rt@example.com", raw, "brandnewpass1")
        assert ok is True
    # token is single-use
    with Session(engine) as s:
        again = auth_service.reset_password_with_token(
            s, "rt@example.com", raw, "another1")
        assert again is False
    assert auth_service.authenticate(_sess(), "rt@example.com", "brandnewpass1")


def test_reset_token_expired_rejected():
    _signup("exp@example.com")
    with Session(engine) as s:
        user, raw = auth_service.create_reset_token(s, "exp@example.com")
        user.reset_expires_at = datetime.utcnow() - timedelta(minutes=1)
        s.add(user)
        s.commit()
    with Session(engine) as s:
        ok = auth_service.reset_password_with_token(s, "exp@example.com", raw, "x12345678")
        assert ok is False


def test_forgot_password_page_is_generic():
    c = TestClient(app)
    r = c.post("/forgot-password", data={"email": "nobody@example.com"})
    # Must not reveal whether the account exists.
    assert "a reset link has been sent" in r.text


# --- admin -------------------------------------------------------------------------

def test_first_user_becomes_admin_bootstrap():
    # Use a dedicated fresh DB so "first user" is deterministic.
    import tempfile as _t
    from sqlmodel import create_engine, SQLModel
    dbf = _t.NamedTemporaryFile(suffix=".db", delete=False)
    eng = create_engine(f"sqlite:///{dbf.name}",
                        connect_args={"check_same_thread": False})
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        first = auth_service.create_user(s, "owner@example.com", "password123")
        second = auth_service.create_user(s, "member@example.com", "password123")
        assert first.is_admin is True       # bootstrap
        assert second.is_admin is False     # not admin
        assert auth_service.is_admin_user(first) is True
        assert auth_service.is_admin_user(second) is False


def test_disabled_user_cannot_authenticate():
    import tempfile as _t
    from sqlmodel import create_engine, SQLModel
    dbf = _t.NamedTemporaryFile(suffix=".db", delete=False)
    eng = create_engine(f"sqlite:///{dbf.name}",
                        connect_args={"check_same_thread": False})
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(eng)
    with Session(eng) as s:
        u = auth_service.create_user(s, "revoked@example.com", "password123")
        u.is_disabled = True
        s.add(u)
        s.commit()
        assert auth_service.authenticate(s, "revoked@example.com", "password123") is None


def test_admin_route_blocks_non_logged_in():
    c = TestClient(app)
    r = c.get("/admin", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]
