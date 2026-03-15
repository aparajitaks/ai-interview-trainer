"""Simple human-like feedback generator for AI Interview Trainer.

This module produces short, actionable messages based on component scores.
The generator is intentionally lightweight and deterministic (no external API
calls) so it is safe to run in tests and CI.
"""

from __future__ import annotations

from typing import List


def generate_feedback(emotion_score: float, eye_score: float, posture_score: float, final_score: float) -> List[str]:
    """Generate a small list of human-like feedback messages.

    Rules (deterministic):
    - If eye_score < 0.4 -> "Maintain better eye contact"
    - If posture_score < 0.4 -> "Sit straight and keep good posture"
    - If emotion_score < 0.4 -> "Try to show confidence in facial expression"
    - final_score band:
      - > 0.75 -> "Excellent performance"
      - 0.5 < final_score <= 0.75 -> "Good performance"
      - 0.3 < final_score <= 0.5 -> "Average performance"
      - <= 0.3 -> "Needs improvement"
    - If none of the first three issue messages were triggered, append
      "Good interview behavior" to reinforce positive signals.

    Returns a list of short messages (strings).
    """
    msgs: List[str] = []

    try:
        if eye_score is None:
            eye_score = 0.0
        if posture_score is None:
            posture_score = 0.0
        if emotion_score is None:
            emotion_score = 0.0
        if final_score is None:
            final_score = 0.0

        if float(eye_score) < 0.4:
            msgs.append("Maintain better eye contact")
        if float(posture_score) < 0.4:
            msgs.append("Sit straight and keep good posture")
        if float(emotion_score) < 0.4:
            msgs.append("Try to show confidence in facial expression")

        fs = float(final_score)
        if fs > 0.75:
            msgs.append("Excellent performance")
        elif 0.5 < fs <= 0.75:
            msgs.append("Good performance")
        elif 0.3 < fs <= 0.5:
            msgs.append("Average performance")
        else:
            msgs.append("Needs improvement")

        if not any(m in msgs for m in ("Maintain better eye contact", "Sit straight and keep good posture", "Try to show confidence in facial expression")):
            msgs.append("Good interview behavior")

    except Exception:
        return ["Feedback unavailable"]

    return msgs
