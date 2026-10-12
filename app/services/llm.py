"""LLM provider abstraction.

With GEMINI_API_KEY set, `complete()` calls the Gemini REST API (free tier).
Without a key it returns None so callers use their deterministic template fallback.
This keeps JobPilot 100% free by default and better with a key.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import get_settings

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


def llm_available() -> bool:
    return get_settings().llm_enabled


def complete(prompt: str, max_output_tokens: int = 1024) -> Optional[str]:
    """Return LLM text, or None if no provider is configured / call fails."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    url = GEMINI_URL.format(model=settings.gemini_model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": 0.4},
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(45.0)) as client:
            resp = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        # Any failure (quota, network) degrades gracefully to the template path.
        return None
