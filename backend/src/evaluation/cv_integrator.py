"""
cv_integrator.py
----------------
Converts computer-vision signals (eye contact %, posture, emotion)
into a single confidence_score (0–100).

Design rationale
~~~~~~~~~~~~~~~~
CV signals measure *presence* and *composure*.  We weight them as:
  • Eye contact   40 % — direct gaze = engaged, confident
  • Posture       35 % — upright = professional composure
  • Emotion       25 % — calm / positive = poised under pressure

If CV data is unavailable the function returns None so the caller
can substitute a text-derived fallback.
"""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Posture → numeric score
# ---------------------------------------------------------------------------

_POSTURE_SCORES = {
    "Good":      100,
    "Slouching":  40,
    "Leaning":    55,
    "Unknown":    50,   # neutral assumption
}

# ---------------------------------------------------------------------------
# Emotion → numeric score
# ---------------------------------------------------------------------------

_EMOTION_SCORES = {
    "Happy":     90,   # positive, engaged
    "Neutral":   75,   # composed, professional
    "Surprise":  55,   # slightly unsettled
    "Sad":       35,   # low energy
    "Angry":     20,   # agitated
    "Unknown":   60,
}


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------


def compute_confidence_score(
    eye_contact_pct: Optional[float] = None,
    posture:         Optional[str]   = None,
    emotion:         Optional[str]   = None,
) -> Optional[int]:
    """
    Combine CV signals into a single confidence score (0–100).

    Parameters
    ----------
    eye_contact_pct : float | None  — percentage, e.g. 72.0
    posture         : str   | None  — "Good" | "Slouching" | "Leaning"
    emotion         : str   | None  — "Happy" | "Neutral" | "Sad" | …

    Returns
    -------
    int  — confidence score 0–100, or None if no CV data provided.
    """
    # Need at least one signal
    if eye_contact_pct is None and posture is None and emotion is None:
        return None

    total_weight = 0.0
    weighted_sum = 0.0

    if eye_contact_pct is not None:
        ec_score     = max(0.0, min(100.0, float(eye_contact_pct)))
        weighted_sum += ec_score * 0.40
        total_weight += 0.40

    if posture is not None:
        p_score       = _POSTURE_SCORES.get(posture, _POSTURE_SCORES["Unknown"])
        weighted_sum += p_score * 0.35
        total_weight += 0.35

    if emotion is not None:
        e_score       = _EMOTION_SCORES.get(emotion, _EMOTION_SCORES["Unknown"])
        weighted_sum += e_score * 0.25
        total_weight += 0.25

    if total_weight == 0:
        return None

    raw = weighted_sum / total_weight
    return int(round(raw))


def compute_confidence_from_text(
    communication_score: int,
    technical_score:     int,
) -> int:
    """
    Fallback: estimate confidence from answer quality when no CV data available.
    Reflects that clear, detailed answers signal composure.
    """
    return int(round(0.5 * communication_score + 0.5 * technical_score))
