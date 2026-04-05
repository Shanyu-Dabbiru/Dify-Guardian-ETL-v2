"""Zone 2 — Real LLM caller for local pipeline simulation.

Supports Anthropic (direct) and OpenAI-compatible providers.
Configured via environment variables:
    LLM_PROVIDER        — "anthropic" (default), "openai", or "openai-compatible"
    ANTHROPIC_API_KEY   — for Anthropic provider
    ANTHROPIC_MODEL     — model name (default: claude-sonnet-4-5-20250514)
    OPENAI_API_KEY      — for OpenAI provider
    OPENAI_BASE_URL     — base URL (default: https://api.openai.com/v1)
    OPENAI_MODEL        — model name (default: gpt-4o)
"""

from __future__ import annotations

import json
import os

import httpx


def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text.strip("` \n")
    return text


# ── Provider: Anthropic ────────────────────────────────────────────────
def call_anthropic(system_prompt: str, user_prompt: str) -> dict:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514")

    payload = {
        "model": model,
        "max_tokens": 1024,
        "temperature": 0,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["content"][0]["text"]

    return json.loads(_strip_json_fences(raw))


# ── Provider: OpenAI-compatible ────────────────────────────────────────
def call_openai_compatible(system_prompt: str, user_prompt: str) -> dict:
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ["OPENAI_API_KEY"]

    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "max_tokens": 1024,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    resp = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]

    return json.loads(_strip_json_fences(raw))


# ── Router ─────────────────────────────────────────────────────────────
_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")

_PROVIDERS = {
    "anthropic": call_anthropic,
    "openai": call_openai_compatible,
    "openai-compatible": call_openai_compatible,
}


def diagnose(drift_report_json: str, system_prompt: str) -> dict:
    """Call the configured LLM with the drift report and return parsed JSON corrections."""
    provider_fn = _PROVIDERS.get(_PROVIDER)
    if provider_fn is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{_PROVIDER}'. "
            f"Supported: {list(_PROVIDERS.keys())}"
        )
    return provider_fn(system_prompt, drift_report_json)
