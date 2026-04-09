"""
transcription.py  (google-genai SDK)
--------------------------------------
Audio-to-text transcription using Gemini 2.0 Flash native audio understanding.

Production path  : Gemini reads audio bytes inline — no separate upload step,
                   no temp files, completely stateless.
                   Requires GEMINI_API_KEY env var.
Development path : Rotating mock answers — zero API keys needed.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_READY  = False
_client        = None

if GEMINI_API_KEY:
    try:
        from google import genai as _genai
        _client       = _genai.Client(api_key=GEMINI_API_KEY)
        _GEMINI_READY = True
        logger.info("Transcription: Gemini 2.0 Flash audio enabled (google-genai SDK).")
    except ImportError:
        logger.warning(
            "google-genai not installed — using mock transcription. "
            "Run: pip install google-genai"
        )
    except Exception as exc:
        logger.warning("Gemini init failed (%s) — mock transcription active.", exc)
else:
    logger.info(
        "GEMINI_API_KEY not set — using mock transcription. "
        "Set the env var for real speech-to-text."
    )

_MODEL = "models/gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# MIME type mapping
# ---------------------------------------------------------------------------

_EXT_MIME = {
    "webm": "audio/webm",
    "mp4":  "audio/mp4",
    "m4a":  "audio/mp4",
    "wav":  "audio/wav",
    "ogg":  "audio/ogg",
    "mp3":  "audio/mpeg",
    "flac": "audio/flac",
}


def _mime(ext: str) -> str:
    return _EXT_MIME.get(ext.lower().lstrip("."), "audio/webm")


# ---------------------------------------------------------------------------
# Mock pool
# ---------------------------------------------------------------------------

_MOCK_POOL = [
    (
        "I have about three years of hands-on experience in this area. "
        "In my last role I built and deployed several production systems, "
        "focusing on reliability and performance. I enjoy diving deep into "
        "technical problems and collaborating closely with cross-functional teams."
    ),
    (
        "That's a great question. My approach is to first understand the root "
        "cause by breaking the problem into smaller components. I then prototype "
        "a solution quickly, gather feedback early, and iterate. For example, "
        "I recently optimised a data pipeline that reduced processing time by 60%."
    ),
    (
        "I believe strong communication and continuous learning are essential. "
        "I stay current by reading research papers, building side projects, "
        "and contributing to open-source. I also document my work thoroughly "
        "so my team can build on it effectively."
    ),
    (
        "In a previous project I had to resolve a technical disagreement with "
        "a senior engineer. I presented data to support my approach, listened "
        "carefully to their concerns, and we found a hybrid solution "
        "that was better than either of our original ideas."
    ),
    (
        "My long-term goal is to become a technical lead and mentor junior "
        "engineers. This role excites me because it aligns with my current "
        "skills and offers challenging problems I thrive on. I see strong "
        "growth potential here over the next few years."
    ),
]

_mock_index = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe(audio_bytes: bytes, audio_ext: str = "webm") -> str:
    """
    Convert raw audio bytes to text.

    Parameters
    ----------
    audio_bytes : bytes  — raw binary audio (WebM, WAV, MP4, etc.)
    audio_ext   : str   — extension without dot e.g. ``"webm"``

    Returns
    -------
    str — transcript, or a rotating mock when Gemini is not configured.
    """
    if _GEMINI_READY and _client is not None:
        return _gemini_transcribe(audio_bytes, audio_ext)
    return _mock_transcribe()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _gemini_transcribe(audio_bytes: bytes, audio_ext: str) -> str:
    """Pass audio inline to Gemini — no temp file or upload needed."""
    from google.genai import types as _gtypes

    mime = _mime(audio_ext)
    logger.debug("Gemini transcribing %d bytes as %s.", len(audio_bytes), mime)

    try:
        audio_part = _gtypes.Part.from_bytes(data=audio_bytes, mime_type=mime)
        response   = _client.models.generate_content(
            model    = _MODEL,
            contents = [
                "You are a professional transcriptionist. "
                "Transcribe the following interview audio verbatim. "
                "Output only the spoken words, nothing else.",
                audio_part,
            ],
        )
        text = (response.text or "").strip()
        logger.debug("Gemini transcript: %s…", text[:80])
        return text or "[No speech detected — please try again]"

    except Exception as exc:
        logger.warning("Gemini transcription error: %s — falling back to mock.", exc)
        return _mock_transcribe()


def _mock_transcribe() -> str:
    global _mock_index
    answer       = _MOCK_POOL[_mock_index % len(_MOCK_POOL)]
    _mock_index += 1
    logger.debug("Mock transcription #%d.", _mock_index)
    return answer
