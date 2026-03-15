"""Thread-safe model loader and cache.

Provides simple, production-friendly helpers to load models once and reuse
them across the process. Uses `ai_models.model_registry` for model names and
delegates actual loading to the existing CV modules where available.

The implementation is intentionally small: a dictionary cache protected by a
lock, per-key loader functions, and logging for observability.
"""
from __future__ import annotations

import threading
from typing import Any, Dict, Optional

from ai_models.model_registry import get_model_name
from utils.logger import get_logger

log = get_logger(__name__)

_MODEL_CACHE: Dict[str, Any] = {}
_CACHE_LOCK = threading.RLock()


def _load_emotion_model() -> Any:
    """Load the emotion model using the cv_models.emotion_model loader.

    This function isolates the import and potential heavyweight initialization
    so callers of the public API remain simple.
    """
    model_name = get_model_name("emotion")
    try:
        from cv_models.emotion_model import load_emotion_model

        log.info("Loading emotion model: %s", model_name)
        model = load_emotion_model(model_name)
        return model
    except Exception as exc:
        log.exception("Failed to load emotion model %s: %s", model_name, exc)
        return None


def _load_pose_model() -> Any:
    """Load the pose detector using cv_models.pose_detector loader.

    Pose detector does not currently accept a model name; we still consult the
    registry for visibility and log the configured name for auditing.
    """
    model_name = get_model_name("pose")
    try:
        from cv_models.pose_detector import load_pose_detector

        log.info("Loading pose detector (registry name: %s)", model_name)
        detector = load_pose_detector()
        return detector
    except Exception as exc:
        log.exception("Failed to load pose detector (registry name=%s): %s", model_name, exc)
        return None


def _load_gaze_model() -> Any:
    """Attempt to load a gaze estimation model if a loader exists.

    If the project does not provide a gaze module the function logs and
    returns None — callers should handle a missing gaze model gracefully.
    """
    model_name = get_model_name("gaze")
    try:
        from cv_models import gaze as gaze_mod  # type: ignore

        if hasattr(gaze_mod, "load_gaze_model"):
            log.info("Loading gaze model: %s", model_name)
            return gaze_mod.load_gaze_model(model_name)
        else:
            log.warning("cv_models.gaze present but has no load_gaze_model()")
            return None
    except Exception:
        log.info("No gaze module available or failed to load gaze model: %s", model_name)
        return None


def _get_or_load(name: str, loader) -> Optional[Any]:
    """Generic helper to get a cached model or load it using loader.

    The function is thread-safe and will ensure the loader is executed at
    most once for a given name.
    """
    model = _MODEL_CACHE.get(name)
    if model is not None:
        return model

    with _CACHE_LOCK:
        model = _MODEL_CACHE.get(name)
        if model is not None:
            return model

        model = loader()
        _MODEL_CACHE[name] = model
        return model


def get_emotion_model() -> Optional[Any]:
    """Return the cached emotion model, loading it if necessary."""
    return _get_or_load("emotion", _load_emotion_model)


def get_pose_model() -> Optional[Any]:
    """Return the cached pose detector, loading it if necessary."""
    return _get_or_load("pose", _load_pose_model)


def get_gaze_model() -> Optional[Any]:
    """Return the cached gaze model, loading it if necessary (may be None)."""
    return _get_or_load("gaze", _load_gaze_model)


if __name__ == "__main__":
    print("Emotion model:", get_emotion_model())
    print("Pose model:", get_pose_model())
    print("Gaze model:", get_gaze_model())
