import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def test_save_job_creates_application_and_detail():
    # Save a job from "search results" into the queue.
    r = client.post("/api/applications/save", json={
        "user_email": "apply@example.com",
        "source": "remotive",
        "title": "Senior Python Engineer",
        "company": "Acme",
        "location": "Remote",
        "remote": True,
        "url": "https://example.com/job/1",
        "description": "We use python and fastapi.",
        "external_id": "job-1",
        "score": 72.5,
    })
    assert r.status_code == 200
    app_id = r.json()["id"]
    assert r.json()["status"] in ("matched", "tailored")

    # Fetch the application detail.
    r = client.get(f"/api/applications/{app_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["job"]["title"] == "Senior Python Engineer"
    assert data["job"]["url"] == "https://example.com/job/1"


def test_save_is_idempotent_per_user_and_job():
    payload = {
        "user_email": "dup@example.com",
        "source": "remoteok",
        "title": "Backend Dev",
        "url": "https://example.com/job/2",
        "external_id": "job-2",
    }
    r1 = client.post("/api/applications/save", json=payload)
    r2 = client.post("/api/applications/save", json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    # Saving the same job twice must not create a second application.
    assert r1.json()["id"] == r2.json()["id"]


def test_ui_save_redirects_to_detail():
    r = client.post("/save", data={
        "user_email": "uiflow@example.com",
        "source": "arbeitnow",
        "title": "Data Engineer",
        "company": "Globex",
        "url": "https://example.com/job/3",
        "external_id": "job-3",
        "score": "40",
    }, follow_redirects=False)
    assert r.status_code == 303
    assert "/application/" in r.headers["location"]


def test_detail_page_renders():
    r = client.post("/api/applications/save", json={
        "user_email": "page@example.com",
        "title": "QA Engineer",
        "url": "https://example.com/job/4",
        "external_id": "job-4",
    })
    app_id = r.json()["id"]
    r = client.get(f"/application/{app_id}?email=page@example.com")
    assert r.status_code == 200
    assert "QA Engineer" in r.text
    assert "Open job posting" in r.text or "No direct URL" in r.text
