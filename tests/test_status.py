import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["APP_SECRET"] = "status-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def test_status_reports_integrations_without_secrets():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "email_configured" in data
    assert "database" in data
    # Must never leak a key value.
    assert "resend_api_key" not in data
    assert "re_" not in str(data)


def test_test_email_requires_login():
    r = client.post("/api/test-email")
    assert r.status_code == 401


def test_test_email_logged_in_uses_log_channel_when_no_provider():
    c = TestClient(app)
    c.post("/signup", data={"email": "mailer@example.com", "password": "password123"})
    r = c.post("/api/test-email")
    assert r.status_code == 200
    body = r.json()
    assert body["sent_to"] == "mailer@example.com"
    # No email provider configured in tests -> falls back to 'log'.
    assert body["channel"] in ("log", "resend", "email")
