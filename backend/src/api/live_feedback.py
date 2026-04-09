"""
live_feedback.py  (API router)
------------------------------
Provides simulated real-time CV feedback during an active interview session.

Endpoint
~~~~~~~~
  GET /live-feedback?session_id=xxx

Returns current eye contact, posture, and emotion signals.

Note
~~~~
This is a simulation layer — the values are randomised within realistic
ranges to demonstrate the UI.  When the real CV pipeline is integrated
with the webcam stream, replace `_simulate_feedback()` with actual
detector output.
"""

from __future__ import annotations

import random
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.interview.session import get_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Live Feedback"])


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class LiveFeedbackResponse(BaseModel):
    eye_contact: str     # "Good" | "Poor"
    posture:     str     # "Good" | "Slouched"
    emotion:     str     # "Neutral" | "Happy" | "Nervous"
    face_detected: bool


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

# Weighted random — biased towards realistic interview behaviour
_EYE_CONTACT_OPTIONS = [("Good", 0.70), ("Poor", 0.30)]
_POSTURE_OPTIONS     = [("Good", 0.65), ("Slouched", 0.35)]
_EMOTION_OPTIONS     = [("Neutral", 0.50), ("Happy", 0.20), ("Nervous", 0.30)]


def _weighted_choice(options: list[tuple[str, float]]) -> str:
    labels, weights = zip(*options)
    return random.choices(labels, weights=weights, k=1)[0]


def _simulate_feedback() -> LiveFeedbackResponse:
    """Generate realistic simulated CV feedback."""
    return LiveFeedbackResponse(
        eye_contact   = _weighted_choice(_EYE_CONTACT_OPTIONS),
        posture       = _weighted_choice(_POSTURE_OPTIONS),
        emotion       = _weighted_choice(_EMOTION_OPTIONS),
        face_detected = random.random() > 0.05,   # 95 % face detected
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/live-feedback",
    response_model = LiveFeedbackResponse,
    summary        = "Get real-time CV feedback for an active interview session",
)
async def get_live_feedback(
    session_id: str = Query(..., description="Active interview session ID"),
) -> LiveFeedbackResponse:
    """
    Return the latest eye contact, posture, and emotion signals
    for the given interview session.

    Currently returns **simulated** values.  Replace with real CV
    detector output once the webcam pipeline is connected.
    """
    session = get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Session '{session_id}' not found.",
        )

    if session.status == "completed":
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "Session has already ended.",
        )

    return _simulate_feedback()
