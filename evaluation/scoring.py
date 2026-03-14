from __future__ import annotations

import logging
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def compute_final_score(
    emotion_score: Optional[float],
    eye_score: Optional[float],
    posture_score: Optional[float],
) -> float:
    """Compute final weighted score from component metrics.

    Weights (product requirement):
      - emotion: 0.3
      - eye: 0.3
      - posture: 0.4

    Args:
        emotion_score: Normalized emotion metric (expected 0..1)
        eye_score: Normalized eye-contact metric (0..1)
        posture_score: Normalized posture metric (0..1)

    Returns:
        final_score clamped to [0,1]
    """
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

    # Weighted sum
    final = 0.3 * e + 0.3 * ey + 0.4 * p

    # Clamp to [0,1] for pipeline stability
    final = float(np.clip(final, 0.0, 1.0))
    log.debug("compute_final_score: e=%.3f ey=%.3f p=%.3f -> final=%.3f", e, ey, p, final)
    return final


def test_scoring() -> None:
    """Headless test that demonstrates the weighted scoring behavior."""
    examples = [
        (1.0, 1.0, 1.0),
        (0.5, 0.5, 0.5),
        (0.0, 0.2, 0.8),
        (None, None, None),
        (1.5, -0.2, 0.7),
    ]
    for e, ey, p in examples:
        s = compute_final_score(e, ey, p)
        log.info("inputs=(%s,%s,%s) -> final=%.3f", e, ey, p, s)


if __name__ == "__main__":
    test_scoring()
