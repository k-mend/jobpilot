import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["APP_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()


def _logged_in_client(email: str) -> TestClient:
    c = TestClient(app)
    r = c.post("/signup", data={"email": email, "password": "password123",
                                "name": "Test"}, follow_redirects=False)
    assert r.status_code == 303
    return c


# --- JSON API still works for the CLI/scan (unauthenticated by design) -------------

def test_api_save_and_detail():
    c = TestClient(app)
    r = c.post("/api/applications/save", json={
        "user_email": "api@example.com", "source": "remotive",
        "title": "Senior Python Engineer", "company": "Acme",
        "url": "https://example.com/job/1", "external_id": "job-1", "score": 72.5,
    })
    assert r.status_code == 200
    app_id = r.json()["id"]
    r = c.get(f"/api/applications/{app_id}")
    assert r.status_code == 200
    assert r.json()["job"]["title"] == "Senior Python Engineer"


# --- UI apply flow requires login --------------------------------------------------

def test_ui_requires_login_redirect():
    c = TestClient(app)
    r = c.get("/queue", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_logged_in_save_and_detail():
    c = _logged_in_client("uiflow@example.com")
    r = c.post("/save", data={
        "source": "arbeitnow", "title": "Data Engineer", "company": "Globex",
        "url": "https://example.com/job/3", "external_id": "job-3", "score": "40",
    }, follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert "/application/" in loc
    r = c.get(loc)
    assert r.status_code == 200
    assert "Data Engineer" in r.text


def test_user_cannot_see_other_users_application():
    c1 = _logged_in_client("owner@example.com")
    r = c1.post("/save", data={"title": "Secret Role",
                               "url": "https://example.com/job/x",
                               "external_id": "job-x"}, follow_redirects=False)
    app_path = r.headers["location"]  # /application/N
    # A different logged-in user must not see it.
    c2 = _logged_in_client("intruder@example.com")
    r = c2.get(app_path)
    assert r.status_code == 200
    assert "Secret Role" not in r.text
    assert "not found" in r.text.lower()
