"""Email (and optional Telegram) notifications for new job matches.

Channels are tried in order, using whichever is configured:
  1. Resend  — HTTP API (RESEND_API_KEY). No App Password needed. Recommended.
  2. Gmail SMTP (SMTP_* vars). Needs 2FA + an App Password.
  3. Telegram (optional).
  4. Log line (always works; nothing leaves the machine).

Empty digests are never sent. See docs/EMAIL_ALERTS.md.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import List

import httpx

from app.config import get_settings

RESEND_URL = "https://api.resend.com/emails"


def _format_digest(user_email: str, matches: List[dict]) -> str:
    lines = [f"JobPilot — {len(matches)} new job match(es) for {user_email}",
             "=" * 48, ""]
    for m in matches:
        lines.append(f"[{m['score']:.0f}] {m['title']} @ {m.get('company', '')}")
        if m.get("url"):
            lines.append(f"    {m['url']}")
    lines += ["", "Open your queue to tailor and apply:",
              f"{get_settings().base_url}/queue"]
    return "\n".join(lines)


def send_digest(user_email: str, matches: List[dict]) -> str:
    """Send a digest of NEW matches. Returns the channel used."""
    if not matches:
        return "skip"  # nothing new — don't send an empty email

    body = _format_digest(user_email, matches)
    subject = f"JobPilot: {len(matches)} new job match(es)"
    settings = get_settings()

    # 1) Resend (HTTP API) — easiest, no App Password.
    if settings.resend_api_key:
        try:
            resp = httpx.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from,
                    "to": [user_email],
                    "subject": subject,
                    "text": body,
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            return "resend"
        except Exception as exc:
            print(f"[notify] resend failed: {exc}")

    # 2) Gmail SMTP.
    if settings.smtp_enabled:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = settings.smtp_from or settings.smtp_user
            msg["To"] = user_email
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return "email"
        except Exception as exc:
            print(f"[notify] smtp failed: {exc}")

    # 3) Telegram (optional).
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": body},
                timeout=20.0,
            )
            return "telegram"
        except Exception as exc:
            print(f"[notify] telegram failed: {exc}")

    # 4) Fallback: log.
    print(body)
    return "log"


def send_test(user_email: str):
    """Like send_digest but returns (channel, detail) so a test endpoint can show the
    real reason a provider failed (e.g. Resend rejecting an unverified recipient)."""
    settings = get_settings()
    sample = [{"title": "Test — your JobPilot email works!", "company": "JobPilot",
               "url": settings.base_url, "score": 100}]
    body = _format_digest(user_email, sample)
    subject = "JobPilot: test email"

    if settings.resend_api_key:
        try:
            resp = httpx.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={"from": settings.resend_from, "to": [user_email],
                      "subject": subject, "text": body},
                timeout=30.0,
            )
            if resp.status_code < 300:
                return "resend", "sent"
            return "resend_error", f"HTTP {resp.status_code}: {resp.text[:300]}"
        except Exception as exc:
            return "resend_error", str(exc)[:300]

    if settings.smtp_enabled:
        channel = send_digest(user_email, sample)
        return channel, "sent via smtp" if channel == "email" else "smtp failed"

    return "log", "no email provider configured"
