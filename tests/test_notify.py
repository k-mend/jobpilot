import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app.config import get_settings  # noqa: E402
from app.services import notify  # noqa: E402

MATCHES = [{"title": "Python Dev", "company": "Acme", "url": "https://x/1", "score": 70}]


def test_skip_when_no_matches():
    assert notify.send_digest("a@b.com", []) == "skip"


def test_log_fallback_when_nothing_configured(monkeypatch):
    # Ensure no channels are configured.
    get_settings.cache_clear()
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    get_settings.cache_clear()
    assert notify.send_digest("a@b.com", MATCHES) == "log"


def test_resend_used_when_key_set(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    get_settings.cache_clear()

    called = {}

    class FakeResp:
        def raise_for_status(self):
            return None

    def fake_post(url, headers=None, json=None, timeout=None):
        called["url"] = url
        called["to"] = json["to"]
        called["auth"] = headers["Authorization"]
        return FakeResp()

    monkeypatch.setattr(notify.httpx, "post", fake_post)
    result = notify.send_digest("me@example.com", MATCHES)

    assert result == "resend"
    assert called["url"] == notify.RESEND_URL
    assert called["to"] == ["me@example.com"]
    assert called["auth"] == "Bearer re_test_key"

    get_settings.cache_clear()
