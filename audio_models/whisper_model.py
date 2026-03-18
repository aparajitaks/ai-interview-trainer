"""Whisper transcription wrapper.

Provides a small, testable `WhisperModel` class that lazily loads the
OpenAI Whisper model (if available) and exposes a `transcribe()` method
that returns the textual transcription for a given audio file.

This module intentionally falls back with clear errors if `whisper` is
not installed so the rest of the project remains usable.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")


class WhisperModel:
    """Lightweight wrapper around openai-whisper model.

    Usage:
        wm = WhisperModel()  # lazy loads model on first transcribe
        text = wm.transcribe("/path/to/audio.wav")
    """

    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None) -> None:
        self._model_name = model_name or WHISPER_MODEL
        self._device = device
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore
        except Exception as exc:  # pragma: no cover - environment dependent
            log.exception("Whisper package is not available: %s", exc)
            raise

        try:
            log.info("Loading whisper model: %s", self._model_name)
            # whisper.load_model handles CPU/GPU selection internally via device param
            if self._device:
                self._model = whisper.load_model(self._model_name, device=self._device)  # type: ignore
            else:
                self._model = whisper.load_model(self._model_name)  # type: ignore
        except Exception as exc:  # pragma: no cover - heavy model load
            log.exception("Failed to load whisper model %s: %s", self._model_name, exc)
            raise

    def transcribe(self, audio_path: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Transcribe the given audio file and return a dict with text and metadata.

        Returns:
            {"text": str, "segments": [...], "raw": <whisper result dict>}
        """
        self._ensure_loaded()
        if not self._model:
            raise RuntimeError("Whisper model not loaded")

        try:
            opts = {}
            if language:
                opts["language"] = language
            log.info("Transcribing audio: %s", audio_path)
            res = self._model.transcribe(audio_path, **opts)  # type: ignore
            text = res.get("text", "") if isinstance(res, dict) else str(res)
            segments = res.get("segments", []) if isinstance(res, dict) else []
            return {"text": text.strip(), "segments": segments, "raw": res}
        except Exception as exc:  # pragma: no cover - depends on whisper runtime
            log.exception("Whisper transcription failed for %s: %s", audio_path, exc)
            return {"text": "", "segments": [], "raw": None}


__all__ = ["WhisperModel"]
