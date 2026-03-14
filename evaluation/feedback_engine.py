from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def generate_feedback(emotion_score: Optional[float], eye_score: Optional[float], posture_score: Optional[float]) -> List[str]:
    """Generate a short list of feedback suggestions given component scores.

    Rules:
      - if eye < 0.5 -> "Maintain better eye contact"
      - if posture < 0.5 -> "Try to sit straight"
      - if emotion < 0.5 -> "Show more confidence"

    Returns a list of strings (possibly empty).
    """
    fb: List[str] = []

    try:
        e = float(emotion_score) if emotion_score is not None else 0.0
    except Exception:
        e = 0.0
    try:
        ey = float(eye_score) if eye_score is not None else 0.0
    except Exception:
        ey = 0.0
    try:
        p = float(posture_score) if posture_score is not None else 0.0
    except Exception:
        p = 0.0

    # Clamp for safety
    e = float(np.clip(e, 0.0, 1.0))
    ey = float(np.clip(ey, 0.0, 1.0))
    p = float(np.clip(p, 0.0, 1.0))

    if ey < 0.5:
        fb.append("Maintain better eye contact")
    if p < 0.5:
        fb.append("Try to sit straight")
    if e < 0.5:
        fb.append("Show more confidence")

    log.debug("generate_feedback: e=%.3f ey=%.3f p=%.3f -> %s", e, ey, p, fb)
    return fb


def test_feedback() -> None:
    """Headless test for feedback engine with example inputs."""
    examples = [
        (0.8, 0.9, 0.95),
        (0.4, 0.6, 0.6),
        (0.6, 0.4, 0.4),
        (None, None, None),
    ]
    for e, ey, p in examples:
        fb = generate_feedback(e, ey, p)
        log.info("scores=(%s,%s,%s) -> feedback=%s", e, ey, p, fb)


if __name__ == "__main__":
    test_feedback()
