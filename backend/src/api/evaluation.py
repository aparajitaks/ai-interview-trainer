"""
evaluation.py  (API router)
---------------------------
FastAPI router exposing the V4 Evaluation Engine.

Endpoints
~~~~~~~~~
  POST /evaluate-interview   — run full NLP + CV evaluation on a session
  GET  /evaluation/{id}      — retrieve a cached result (TODO: add persistence)

Mount in app.py:
    from src.api.evaluation import router as evaluation_router
    app.include_router(evaluation_router)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.evaluation.evaluator import EvaluationResult, evaluate_session
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/evaluate", tags=["Evaluation Engine"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EvaluateRequest(BaseModel):
    """Body for POST /evaluate-interview (JSON variant)."""
    session_id:      str           = Field(..., description="Interview session UUID")
    # Optional CV signals from a parallel video-analysis run
    eye_contact_pct: Optional[float] = Field(None, ge=0, le=100, description="Eye-contact % from video analysis")
    posture:         Optional[str]   = Field(None, description="'Good' | 'Slouching' | 'Leaning'")
    emotion:         Optional[str]   = Field(None, description="'Happy' | 'Neutral' | 'Sad' | …")


class RoundResultSchema(BaseModel):
    question:       str
    answer:         str
    relevance:      int
    completeness:   int
    clarity:        int
    round_feedback: str


class EvaluationResponse(BaseModel):
    session_id:          str
    role:                str
    technical_score:     int
    communication_score: int
    confidence_score:    int
    overall_score:       int
    overall_label:       str
    feedback:            str
    rounds:              List[RoundResultSchema]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/interview",
    response_model  = EvaluationResponse,
    summary         = "Run V4 evaluation engine on a completed interview session",
)
async def evaluate_interview(body: EvaluateRequest) -> EvaluationResponse:
    """
    Run the full NLP + CV scoring + feedback generation pipeline on a session.

    The session must have at least one answered round.
    CV signals (eye_contact_pct, posture, emotion) are optional — supply them
    if you ran a parallel video analysis; otherwise confidence is derived from
    answer quality.

    Returns per-round breakdowns and four aggregate scores.
    """
    logger.info(
        "Evaluation request — session=%s  cv=%s",
        body.session_id[:8],
        "provided" if body.eye_contact_pct is not None else "none",
    )

    try:
        result: EvaluationResult = evaluate_session(
            session_id      = body.session_id,
            eye_contact_pct = body.eye_contact_pct,
            posture         = body.posture,
            emotion         = body.emotion,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Evaluation pipeline error: %s", exc)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail      = f"Evaluation failed: {exc}",
        ) from exc

    return EvaluationResponse(**result.to_dict())


@router.post(
    "/interview/form",
    response_model  = EvaluationResponse,
    summary         = "Run evaluation (form-data variant for easy curl testing)",
    include_in_schema = False,   # Hidden in docs — use the JSON endpoint
)
async def evaluate_interview_form(
    session_id:      str            = Form(...),
    eye_contact_pct: Optional[float] = Form(None),
    posture:         Optional[str]   = Form(None),
    emotion:         Optional[str]   = Form(None),
) -> JSONResponse:
    """Form-data variant — same logic as the JSON endpoint."""
    body = EvaluateRequest(
        session_id      = session_id,
        eye_contact_pct = eye_contact_pct,
        posture         = posture,
        emotion         = emotion,
    )
    return await evaluate_interview(body)
