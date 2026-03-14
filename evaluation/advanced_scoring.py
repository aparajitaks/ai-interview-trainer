"""Advanced scoring utilities.

Provides a weighted scoring function for emotion, eye (gaze), and posture
components. The function is production-oriented: it reads optional weight
overrides from environment variables, logs the chosen weights, clamps the
final score to [0.0, 1.0], and tolerates missing/null inputs.

Environment variables (optional):
 - AIIT_EMOTION_WEIGHT (float)
 - AIIT_EYE_WEIGHT (float)
 - AIIT_POSTURE_WEIGHT (float)
 - AIIT_ROLE (string, e.g., 'candidate', 'interviewer')
 - AIIT_ROLE_WEIGHT (float) -- multiplies the aggregated score
"""
from __future__ import annotations

import os
import logging
from typing import Optional

from utils.logger import get_logger

log = get_logger(__name__)


def _parse_env_weight(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return float(default)
    try:
        return float(v)
    except Exception:
        log.warning("Invalid %s=%r, falling back to %s", name, v, default)
        return float(default)


def _coerce_score(x: Optional[float]) -> float:
    try:
        if x is None:
            return 0.0
        return float(x)
    except Exception:
        log.warning("Non-numeric score encountered: %r; treating as 0.0", x)
        return 0.0


def compute_score(emotion, eye, posture) -> float:
    """Compute a weighted aggregated score in [0.0, 1.0].

    - Reads optional overrides for component weights from environment.
    - Reads optional role weight multiplier from AIIT_ROLE_WEIGHT.
    - Treats None or invalid component values as 0.0.

    Parameters:
    - emotion: float-like in [0,1] (or None)
    - eye: float-like in [0,1] (or None)
    - posture: float-like in [0,1] (or None)

    Returns:
    - float in [0.0, 1.0]
    """
    # Component weights (defaults can be tuned)
    default_emotion_w = 0.4
    default_eye_w = 0.3
    default_posture_w = 0.3

    w_emotion = _parse_env_weight("AIIT_EMOTION_WEIGHT", default_emotion_w)
    w_eye = _parse_env_weight("AIIT_EYE_WEIGHT", default_eye_w)
    w_posture = _parse_env_weight("AIIT_POSTURE_WEIGHT", default_posture_w)

    # Normalize weights to sum to 1 if they don't already
    total_w = w_emotion + w_eye + w_posture
    if total_w <= 0:
        log.warning("Component weights sum to %s; falling back to defaults", total_w)
        w_emotion, w_eye, w_posture = default_emotion_w, default_eye_w, default_posture_w
        total_w = w_emotion + w_eye + w_posture

    w_emotion /= total_w
    w_eye /= total_w
    w_posture /= total_w

    # Role-based multiplier
    role = os.getenv("AIIT_ROLE", "candidate")
    role_weight_env = os.getenv("AIIT_ROLE_WEIGHT")
    if role_weight_env is not None:
        try:
            role_weight = float(role_weight_env)
        except Exception:
            log.warning("Invalid AIIT_ROLE_WEIGHT=%r; using 1.0", role_weight_env)
            role_weight = 1.0
    else:
        # sensible defaults for roles
        role_defaults = {
            "candidate": 1.0,
            "interviewer": 0.8,
            "recruiter": 0.9,
            "manager": 1.0,
        }
        role_weight = float(role_defaults.get(role, 1.0))

    # Coerce component scores
    e = _coerce_score(emotion)
    ey = _coerce_score(eye)
    p = _coerce_score(posture)

    # Ensure components are in [0,1] before combining
    def _clamp01(v: float) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except Exception:
            return 0.0

    e = _clamp01(e)
    ey = _clamp01(ey)
    p = _clamp01(p)

    raw = e * w_emotion + ey * w_eye + p * w_posture
    scored = raw * role_weight

    # Final clamp
    final = max(0.0, min(1.0, float(scored)))

    log.info(
        "compute_score: components=(emotion=%.3f,eye=%.3f,posture=%.3f) weights=(%.3f,%.3f,%.3f) role=%s(role_w=%.3f) raw=%.3f final=%.3f",
        e,
        ey,
        p,
        w_emotion,
        w_eye,
        w_posture,
        role,
        role_weight,
        raw,
        final,
    )

    return float(final)


if __name__ == "__main__":
    # Quick manual checks
    print("Balanced inputs (0.8,0.8,0.8):", compute_score(0.8, 0.8, 0.8))
    print("Missing components (None,0.5,0.5):", compute_score(None, 0.5, 0.5))
    os_role = os.getenv("AIIT_ROLE")
    if os_role:
        print("AIIT_ROLE env is set to:", os_role)
