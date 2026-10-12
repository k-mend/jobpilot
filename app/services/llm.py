"""LLM provider abstraction.

`complete(prompt)` routes to whichever provider is configured:
  1. OpenRouter  (if OPENROUTER_API_KEY is set) — has genuinely free models.
  2. Gemini      (if GEMINI_API_KEY is set)      — free tier available.
  3. Neither     -> returns None, so callers use their deterministic template.

This keeps JobPilot 100% free by default and better with a (free) key.
Any failure (quota, network, bad key) degrades gracefully to None.
"""
from __future__ import annotations

from typing import Optional

import httpx

from app.config import get_settings

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def llm_available() -> bool:
    return get_settings().llm_enabled


def complete(prompt: str, max_output_tokens: int = 1024) -> Optional[str]:
    """Return LLM text, or None if no provider is configured / the call fails."""
    settings = get_settings()
    provider = settings.active_provider
    if provider == "openrouter":
        return _complete_openrouter(prompt, max_output_tokens)
    if provider == "gemini":
        return _complete_gemini(prompt, max_output_tokens)
    return None


def _complete_openrouter(prompt: str, max_output_tokens: int) -> Optional[str]:
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Optional attribution headers recommended by OpenRouter.
        "HTTP-Referer": "https://github.com/k-mend/jobpilot",
        "X-Title": "JobPilot",
    }
    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_output_tokens,
        "temperature": 0.4,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            resp = client.post(OPENROUTER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        text = (choices[0].get("message", {}).get("content") or "").strip()
        return text or None
    except Exception:
        return None


def _complete_gemini(prompt: str, max_output_tokens: int) -> Optional[str]:
    settings = get_settings()
    url = GEMINI_URL.format(model=settings.gemini_model)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": 0.4},
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(45.0)) as client:
            resp = client.post(
                url, params={"key": settings.gemini_api_key}, json=payload
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
        return None
