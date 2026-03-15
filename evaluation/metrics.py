from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _safe_float(x: Optional[float]) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def compute_emotion_metric(emotion_score: Optional[float]) -> float:
    """Normalize an emotion score to [0,1].

    Args:
        emotion_score: Raw emotion score (model confidence or heuristic mapping).

    Returns:
        A float in [0,1].
    """
    s = _safe_float(emotion_score)
    out = float(np.clip(s, 0.0, 1.0))
    log.debug("compute_emotion_metric: in=%s out=%s", emotion_score, out)
    return out


def compute_eye_metric(eye_score: Optional[float]) -> float:
    """Normalize an eye-contact score to [0,1]."""
    s = _safe_float(eye_score)
    out = float(np.clip(s, 0.0, 1.0))
    log.debug("compute_eye_metric: in=%s out=%s", eye_score, out)
    return out


def compute_posture_metric(posture_score: Optional[float]) -> float:
    """Normalize a posture score to [0,1]."""
    s = _safe_float(posture_score)
    out = float(np.clip(s, 0.0, 1.0))
    log.debug("compute_posture_metric: in=%s out=%s", posture_score, out)
    return out


def test_metrics() -> None:
    """Simple headless test for metrics module.

    Runs a few example inputs and logs the normalized outputs.
    """
    examples = [None, -0.5, 0.0, 0.3, 0.75, 1.2, 2.0]
    for e in examples:
        em = compute_emotion_metric(e)
        ey = compute_eye_metric(e)
        ps = compute_posture_metric(e)
        log.info("input=%s -> emotion=%.3f eye=%.3f posture=%.3f", e, em, ey, ps)


if __name__ == "__main__":
    test_metrics()
