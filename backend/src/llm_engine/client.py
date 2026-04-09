"""
client.py
---------
Gemini client singleton with retry logic and error handling.

Reads GEMINI_API_KEY from environment. Exposes a simple `call_llm()`
wrapper that handles retries, timeouts, and JSON mode.

Usage
~~~~~
    from src.llm_engine.client import call_llm, is_ready

    if is_ready():
        result = call_llm(prompt, json_mode=True)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini-only client (project standard)
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_provider = None  # "gemini" | None
_client = None
_gtypes = None

_GEMINI_MODEL = "models/gemini-2.5-flash-lite"

# Prefer Gemini when GEMINI_API_KEY is provided (project standard)
if GEMINI_API_KEY:
    try:
        from google import genai as _genai
        from google.genai import types as _gt

        _client = _genai.Client(api_key=GEMINI_API_KEY)
        _gtypes = _gt
        _provider = "gemini"
        logger.info("LLM Engine: Gemini client ready (model=%s).", _GEMINI_MODEL)
    except Exception as exc:
        logger.warning("Gemini client init failed (%s).", exc)

def is_ready() -> bool:
    """Return True if an LLM provider is configured."""
    return _provider == "gemini"


def call_llm(
    prompt: str,
    json_mode: bool = False,
    max_retries: int = 2,
    timeout_ms: int = 15_000,
) -> str:
    """
    Call the configured LLM provider and return the raw text output.

    If `json_mode` is True, instruct the model to return JSON (providers
    are asked via different knobs). This wrapper implements simple
    retry/backoff and normalises the raw text result.
    """
    if _provider is None:
        raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY.")

    last_exc: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.perf_counter()

            if _provider == "gemini" and _client is not None:
                config = None
                if json_mode and _gtypes is not None:
                    config = _gtypes.GenerateContentConfig(response_mime_type="application/json")
                resp = _client.models.generate_content(model=_GEMINI_MODEL, contents=prompt, config=config)
                text = (resp.text or "").strip()

            else:
                raise RuntimeError("LLM provider misconfigured")

            elapsed = (time.perf_counter() - t0) * 1000
            logger.debug("LLM call succeeded — provider=%s attempt=%d elapsed=%.0fms chars=%d", _provider, attempt, elapsed, len(text))
            return text

        except Exception as exc:
            last_exc = exc
            logger.warning("LLM call failed (provider=%s attempt %d/%d): %s", _provider, attempt, max_retries, exc)
            if attempt < max_retries:
                time.sleep(0.5 * attempt)

    raise last_exc  # type: ignore[misc]


def call_llm_json(prompt: str, max_retries: int = 2) -> dict:
    """Call the LLM and parse a JSON response. Raises on invalid JSON."""
    raw = call_llm(prompt, json_mode=True, max_retries=max_retries)
    # Some models may return extra text — attempt to locate the first
    # JSON object in the response text for robust parsing.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract a JSON substring
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start:end+1]
            return json.loads(snippet)
        raise
