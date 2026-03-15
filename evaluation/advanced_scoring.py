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
from typing import Optional, Dict
import math

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


def compute_score(emotion, eye, posture, stability: Optional[float] = None, confidence: Optional[float] = None, missing_detectors: Optional[Dict[str, bool]] = None) -> float:
    """Compute a weighted aggregated score in [0.0, 1.0].

    - Reads optional overrides for component weights from environment.
    - Reads optional role weight multiplier from AIIT_ROLE_WEIGHT.
    - Treats None or invalid component values as 0.0.

    Parameters:
    - emotion: float-like in [0,1] (or None)
    - eye: float-like in [0,1] (or None)
        - posture: float-like in [0,1] (or None)
        - stability: optional float-like in [0,1]. If not provided, stability is
            derived from the consistency of the three main components (lower stddev -> higher stability).
        - confidence: optional overall confidence in [0,1] which scales the final score.
        - missing_detectors: optional dict signalling missing detectors, e.g. {"pose": True}

    Returns:
    - float in [0.0, 1.0]
    """
    default_emotion_w = 0.3
    default_eye_w = 0.3
    default_posture_w = 0.3
    default_stability_w = 0.1

    em_env = os.getenv("AIIT_EMOTION_WEIGHT")
    eye_env = os.getenv("AIIT_EYE_WEIGHT")
    post_env = os.getenv("AIIT_POSTURE_WEIGHT")
    stab_env = os.getenv("AIIT_STABILITY_WEIGHT")

    if stab_env is not None:
        w_emotion = _parse_env_weight("AIIT_EMOTION_WEIGHT", default_emotion_w)
        w_eye = _parse_env_weight("AIIT_EYE_WEIGHT", default_eye_w)
        w_posture = _parse_env_weight("AIIT_POSTURE_WEIGHT", default_posture_w)
        w_stability = _parse_env_weight("AIIT_STABILITY_WEIGHT", default_stability_w)
        total_w = w_emotion + w_eye + w_posture + w_stability
        if total_w <= 0:
            log.warning("Component weights sum to %s; falling back to defaults", total_w)
            w_emotion, w_eye, w_posture, w_stability = (
                default_emotion_w,
                default_eye_w,
                default_posture_w,
                default_stability_w,
            )
            total_w = sum((w_emotion, w_eye, w_posture, w_stability))
        w_emotion /= total_w
        w_eye /= total_w
        w_posture /= total_w
        w_stability /= total_w
    elif any(v is not None for v in (em_env, eye_env, post_env)):
        w_emotion = _parse_env_weight("AIIT_EMOTION_WEIGHT", default_emotion_w)
        w_eye = _parse_env_weight("AIIT_EYE_WEIGHT", default_eye_w)
        w_posture = _parse_env_weight("AIIT_POSTURE_WEIGHT", default_posture_w)
        total_w = w_emotion + w_eye + w_posture
        if total_w <= 0:
            log.warning("Component weights sum to %s; falling back to defaults", total_w)
            w_emotion, w_eye, w_posture = default_emotion_w, default_eye_w, default_posture_w
            total_w = w_emotion + w_eye + w_posture
        w_emotion /= total_w
        w_eye /= total_w
        w_posture /= total_w
        w_stability = 0.0
    else:
        w_emotion = default_emotion_w
        w_eye = default_eye_w
        w_posture = default_posture_w
        w_stability = default_stability_w
        total_w = w_emotion + w_eye + w_posture + w_stability
        w_emotion /= total_w
        w_eye /= total_w
        w_posture /= total_w
        w_stability /= total_w

    role = os.getenv("AIIT_ROLE", "candidate")
    role_weight_env = os.getenv("AIIT_ROLE_WEIGHT")
    if role_weight_env is not None:
        try:
            role_weight = float(role_weight_env)
        except Exception:
            log.warning("Invalid AIIT_ROLE_WEIGHT=%r; using 1.0", role_weight_env)
            role_weight = 1.0
    else:
        role_defaults = {
            "candidate": 1.0,
            "interviewer": 0.8,
            "recruiter": 0.9,
            "manager": 1.0,
        }
        role_weight = float(role_defaults.get(role, 1.0))

    e = _coerce_score(emotion)
    ey = _coerce_score(eye)
    p = _coerce_score(posture)
    s = _coerce_score(stability) if stability is not None else None
    conf = _coerce_score(confidence) if confidence is not None else 1.0

    def _clamp01(v: float) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except Exception:
            return 0.0

    e = _clamp01(e)
    ey = _clamp01(ey)
    p = _clamp01(p)
    if s is None:
        comps = [e, ey, p]
        if all(v == 0.0 for v in comps):
            s = 0.0
        else:
            mean = sum(comps) / len(comps)
            var = sum((v - mean) ** 2 for v in comps) / len(comps)
            std = math.sqrt(var)
            s = _clamp01(1.0 - std)
    else:
        s = _clamp01(s)

    conf = _clamp01(conf)

    raw = e * w_emotion + ey * w_eye + p * w_posture + s * w_stability
    scored = raw * role_weight

    missing_penalty_per = _parse_env_weight("AIIT_MISSING_PENALTY", 0.1)
    missing_count = 0
    if missing_detectors:
        missing_count = sum(1 for v in missing_detectors.values() if v)
    if missing_count > 0:
        penalty = missing_count * missing_penalty_per
        log.info("Missing detectors: %s -> applying penalty=%.3f", missing_detectors, penalty)
        scored = max(0.0, scored - penalty)

    scored = scored * conf

    final = max(0.0, min(1.0, float(scored)))

    if final > 1.0 - 1e-12:
        final = 1.0

    if e == 0.0 and ey == 0.0 and p == 0.0 and s == 0.0:
        final = 0.0

    log.info(
        "compute_score: components=(emotion=%.3f,eye=%.3f,posture=%.3f,stability=%.3f) weights=(%.3f,%.3f,%.3f,%.3f) role=%s(role_w=%.3f) conf=%.3f missing_count=%d raw=%.3f final=%.3f",
        e,
        ey,
        p,
        s,
        w_emotion,
        w_eye,
        w_posture,
        w_stability,
        role,
        role_weight,
        conf,
        missing_count,
        raw,
        final,
    )

    return float(final)


if __name__ == "__main__":
    print("Balanced inputs (0.8,0.8,0.8):", compute_score(0.8, 0.8, 0.8))
    print("Missing components (None,0.5,0.5):", compute_score(None, 0.5, 0.5))
    os_role = os.getenv("AIIT_ROLE")
    if os_role:
        print("AIIT_ROLE env is set to:", os_role)
