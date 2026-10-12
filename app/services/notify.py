"""Notifications. All channels are optional; default is a no-op log line.

Configure via env (SMTP_* or TELEGRAM_*) to enable. Kept dependency-free (stdlib only).
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from typing import List


def _format_digest(user_email: str, matches: List[dict]) -> str:
    lines = [f"JobPilot digest for {user_email}", "=" * 40, ""]
    for m in matches:
        lines.append(f"[{m['score']:.0f}] {m['title']} @ {m['company']}")
        if m.get("url"):
            lines.append(f"    {m['url']}")
    if not matches:
        lines.append("No new matches this run.")
    return "\n".join(lines)


def send_digest(user_email: str, matches: List[dict]) -> str:
    """Send a digest via whichever channel is configured. Returns the channel used."""
    body = _format_digest(user_email, matches)

    # Email via SMTP if configured.
    host = os.getenv("SMTP_HOST")
    if host:
        try:
            msg = MIMEText(body)
            msg["Subject"] = f"JobPilot: {len(matches)} new job match(es)"
            msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "jobpilot"))
            msg["To"] = user_email
            with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587"))) as server:
                server.starttls()
                user = os.getenv("SMTP_USER")
                pwd = os.getenv("SMTP_PASSWORD")
                if user and pwd:
                    server.login(user, pwd)
                server.send_message(msg)
            return "email"
        except Exception:
            pass  # fall through to log

    # Telegram if configured.
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
        except Exception:
            pass

    # Default: just log.
    print(body)
    return "log"
