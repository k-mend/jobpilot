"""Email (and optional Telegram) notifications for new job matches.

Primary channel is Gmail SMTP, configured via Settings (SMTP_* env vars). If SMTP isn't
configured, we fall back to Telegram (if set) and finally to a log line. Stdlib-only for
email so there's no extra dependency.

See docs/EMAIL_ALERTS.md for the Gmail App Password setup.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import List

from app.config import get_settings


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
    """Send a digest of NEW matches. Returns the channel used ('email'/'telegram'/'log'/'skip')."""
    if not matches:
        return "skip"  # nothing new — don't send an empty email

    body = _format_digest(user_email, matches)
    settings = get_settings()

    # 1) Email via SMTP (Gmail recommended).
    if settings.email_enabled:
        try:
            msg = MIMEText(body)
            msg["Subject"] = f"JobPilot: {len(matches)} new job match(es)"
            msg["From"] = settings.smtp_from or settings.smtp_user
            msg["To"] = user_email
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return "email"
        except Exception as exc:
            print(f"[notify] email failed: {exc}")

    # 2) Telegram (optional).
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            import httpx

            httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": body},
                timeout=20.0,
            )
            return "telegram"
        except Exception as exc:
            print(f"[notify] telegram failed: {exc}")

    # 3) Fallback: log.
    print(body)
    return "log"
