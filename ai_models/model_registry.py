"""Simple model registry helpers.

This module centralizes the model identifiers used by the codebase.
It reads names from environment variables using ``os.getenv`` so the
deployment can override model choices without touching code.

Only tiny, safe helpers are provided — no heavy logic or network calls.
Logging is used for visibility when the helper is used at runtime.
"""
from __future__ import annotations

import os
from typing import Final

from utils.logger import get_logger

log = get_logger(__name__)

# Model names are read from environment variables. Provide sensible
# defaults so the application can run in development without additional
# configuration. These are immutable constants (Final) for readability.
EMOTION_MODEL: Final[str] = os.getenv("EMOTION_MODEL", "microsoft/resnet-50")
POSE_MODEL: Final[str] = os.getenv("POSE_MODEL", "mediapipe/pose")
GAZE_MODEL: Final[str] = os.getenv("GAZE_MODEL", "gaze-estimation/default")


def get_model_name(key: str) -> str:
    """Return the model name for the given key.

    Args:
        key: one of 'emotion', 'pose', or 'gaze' (case-insensitive).

    Returns:
        The configured model name (may be the default) or an empty string
        if the key is unrecognized.

    Notes:
        This helper is intentionally minimal — callers should handle an
        empty-string return value as "not configured".
    """
    k = (key or "").strip().lower()
    if k == "emotion":
        log.debug("Resolved emotion model: %s", EMOTION_MODEL)
        return EMOTION_MODEL
    if k == "pose":
        log.debug("Resolved pose model: %s", POSE_MODEL)
        return POSE_MODEL
    if k == "gaze":
        log.debug("Resolved gaze model: %s", GAZE_MODEL)
        return GAZE_MODEL

    log.warning("Unknown model key requested: %s", key)
    return ""


if __name__ == "__main__":
    # Simple CLI/test to print resolved model names. Safe to run in CI or
    # locally to verify environment overrides.
    print("EMOTION_MODEL=", EMOTION_MODEL)
    print("POSE_MODEL=", POSE_MODEL)
    print("GAZE_MODEL=", GAZE_MODEL)