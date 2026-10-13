import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["APP_SECRET"] = "unit-test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

init_db()
client = TestClient(app)


def test_password_hash_roundtrip():
    h = auth_service.hash_password("hunter2password")
    assert h != "hunter2password"
    assert auth_service.verify_password("hunter2password", h)
    assert not auth_service.verify_password("wrong", h)


def test_session_token_roundtrip():
    token = auth_service.make_session_token(42)
    assert auth_service.read_session_token(token) == 42
    assert auth_service.read_session_token("tampered") is None


def test_signup_sets_cookie_and_logs_in():
    r = client.post("/signup", data={"email": "a@example.com",
                                     "password": "password123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert auth_service.COOKIE_NAME in r.cookies


def test_signup_rejects_short_password():
    r = client.post("/signup", data={"email": "short@example.com", "password": "123"})
    assert r.status_code == 200
    assert "at least 8" in r.text


def test_duplicate_signup_rejected():
    client.post("/signup", data={"email": "dup@example.com", "password": "password123"})
    c2 = TestClient(app)
    r = c2.post("/signup", data={"email": "dup@example.com", "password": "password123"})
    assert "already exists" in r.text


def test_login_wrong_password():
    client.post("/signup", data={"email": "b@example.com", "password": "password123"})
    c = TestClient(app)
    r = c.post("/login", data={"email": "b@example.com", "password": "nope"})
    assert "Wrong email or password" in r.text


def test_login_then_access_protected_route():
    client.post("/signup", data={"email": "c@example.com", "password": "password123"})
    c = TestClient(app)
    c.post("/login", data={"email": "c@example.com", "password": "password123"})
    r = c.get("/queue")
    assert r.status_code == 200
    assert "dashboard" in r.text.lower()


def test_logout_clears_session():
    c = TestClient(app)
    c.post("/signup", data={"email": "d@example.com", "password": "password123"})
    c.get("/logout")
    r = c.get("/queue", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]
