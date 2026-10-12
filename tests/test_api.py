import os
import tempfile

import pytest

# Use a temp SQLite DB for tests before importing the app.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.schemas import RawJob  # noqa: E402
from app.services import queue as queue_service  # noqa: E402

# Ensure tables exist (TestClient without a context manager won't run lifespan).
init_db()


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Replace real source fetching with a deterministic fake."""
    def fake_fetch_all(query, settings=None):
        return [
            RawJob(source="fake", external_id="1",
                   title="Senior Python Backend Engineer",
                   company="Acme", description="python fastapi backend", remote=True),
            RawJob(source="fake", external_id="2",
                   title="Marketing Lead", company="Globex",
                   description="campaigns"),
        ]
    monkeypatch.setattr(queue_service, "fetch_all", fake_fetch_all)


client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_home_page_boots():
    r = client.get("/")
    assert r.status_code == 200
    assert "JobPilot" in r.text


def test_search_endpoint_ranks():
    r = client.post("/api/search", json={"query": "remote python backend"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    # The python job should rank first.
    assert "Python" in data[0]["title"]


def test_search_ui_page():
    r = client.post("/search", data={"query": "python", "user_email": ""})
    assert r.status_code == 200
    assert "Matches" in r.text


def test_full_user_flow():
    # create user
    r = client.post("/api/users", data={"email": "flow@example.com", "name": "Flow"})
    assert r.status_code == 200
    uid = r.json()["id"]

    # upload a CV
    r = client.post(
        f"/api/users/{uid}/cv",
        files={"file": ("cv.txt", b"Python FastAPI engineer, 5 years", "text/plain")},
    )
    assert r.status_code == 200
    assert "python" in r.json()["skills"]

    # create a saved search and scan it
    r = client.post("/api/saved-searches",
                    json={"user_email": "flow@example.com",
                          "description": "remote python backend"})
    assert r.status_code == 200
    sid = r.json()["id"]

    r = client.post(f"/api/saved-searches/{sid}/scan")
    assert r.status_code == 200
    assert len(r.json()["matches"]) >= 1

    # applications should now exist
    r = client.get(f"/api/users/{uid}/applications")
    assert r.status_code == 200
    apps = r.json()
    assert len(apps) >= 1

    # advance one through the workflow
    app_id = apps[0]["id"]
    r = client.post(f"/api/applications/{app_id}/status",
                    json={"status": "ready"})
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
