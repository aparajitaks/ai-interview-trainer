"""
interview.py  (API router)
--------------------------
FastAPI router for the live AI interview system.

Endpoints
~~~~~~~~~
  POST /interview/start           – Create session, return first question
  POST /interview/submit-answer   – Transcribe audio, evaluate, return next Q
  POST /interview/skip-question   – Skip current question, get next
  POST /interview/end             – Generate final holistic evaluation
  GET  /interview/session/{id}    – Debug: inspect session state
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.interview.llm import (
    generate_first_question_payload,
    generate_next_question_payload,
)
from src.interview.session import (
    InterviewSession,
    add_question,
    add_question_v5,
    complete_session,
    create_session,
    get_session,
    record_answer,
    skip_round,
)
from src.interview.transcription import transcribe
from src.llm_engine import (
    RoundMemory,
    generate_next_step,
    is_ready as llm_ready,
)
from src.llm_engine.final_report import build_final_report
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/interview", tags=["Live Interview"])
public_router = APIRouter(tags=["Live Interview Compatibility"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class StartRequest(BaseModel):
    role:       str = Field("Software Engineer", min_length=1, max_length=120)
    max_rounds: int = Field(5, ge=1, le=10)


class StartResponse(BaseModel):
    session_id:   str
    question:     str
    type:         Literal["coding", "text"] = "text"
    round_number: int
    total_rounds: int


class SubmitResponse(BaseModel):
    transcript:       str
    feedback:         str
    score:            Optional[int] = None
    expected_answer:  Optional[str] = None
    gap_analysis:     Optional[str] = None
    improvement_suggestion: Optional[str] = None
    explanation:      Optional[str] = None
    how_to_answer:    Optional[str] = None
    key_points:       Optional[list[str]] = None
    example:          Optional[str] = None
    next_question:    Optional[str]
    type:             Literal["coding", "text"] = "text"
    is_last:          bool = False
    message:          Optional[str] = None
    is_complete:      bool
    round_number:     int
    total_rounds:     int
    follow_up:        bool           = False
    is_follow_up:     Optional[bool] = None
    follow_up_reason: Optional[str]  = None


class SkipResponse(BaseModel):
    skipped:       bool = True
    next_question: Optional[str]
    is_complete:   bool
    round_number:  int
    total_rounds:  int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_session(session_id: str) -> InterviewSession:
    s = get_session(session_id)
    if not s:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Session '{session_id}' not found.",
        )
    return s


def _build_history(session: InterviewSession) -> list[RoundMemory]:
    memories: list[RoundMemory] = []
    for r in session.rounds:
        if r.answer is None:
            continue
        memories.append(
            RoundMemory(
                question=r.question,
                answer=r.answer,
                score=r.score,
                feedback=r.feedback,
                expected_answer=r.expected_answer,
                gap_analysis=r.gap_analysis,
                improvement=r.improvement,
                is_follow_up=r.is_follow_up,
                follow_up_depth=r.follow_up_depth,
            )
        )
    return memories


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/start", response_model=StartResponse, summary="Start a new interview session")
async def start_interview(body: StartRequest) -> StartResponse:
    """
    Create a new interview session, generate the opening question.

    - **role**: Job title the candidate is being interviewed for.
    - **max_rounds**: How many question-answer rounds (default 5).
    """
    session = create_session(role=body.role.strip(), max_rounds=body.max_rounds)
    question, question_type = generate_first_question_payload(session.role)
    add_question(session.session_id, question)

    logger.info(
        "Interview started — session=%s  role='%s'  rounds=%d",
        session.session_id[:8], session.role, session.max_rounds,
    )
    return StartResponse(
        session_id   = session.session_id,
        question     = question,
        type         = question_type,
        round_number = 1,
        total_rounds = session.max_rounds,
    )


@public_router.post("/start-interview", response_model=StartResponse, summary="Start interview (compat route)")
async def start_interview_compat(body: StartRequest) -> StartResponse:
    return await start_interview(body)


@router.post(
    "/submit-answer",
    response_model  = SubmitResponse,
    summary         = "Submit a recorded audio answer",
)
async def submit_answer(
    request: Request,
    session_id: Optional[str] = Form(None, description="Session ID from /start"),
    audio: Optional[UploadFile] = File(None, description="Recorded audio (WebM/M4A/WAV)"),
    answer: Optional[str] = Form(None, description="Direct text/code answer"),
) -> SubmitResponse:
    """
    Live interview flow:
    1. Transcribe audio answer.
    2. Evaluate with LLM (Gemini).
    3. Apply cross-questioning logic.
    4. Persist rich learning feedback.
    """
    if session_id is None:
        try:
            json_body = await request.json()
        except Exception:
            json_body = {}
        session_id = json_body.get("session_id")
        answer = answer or json_body.get("answer")

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="session_id is required.",
        )

    session = _require_session(session_id)

    if session.status == "completed":
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "This interview session has already ended.",
        )

    # ── Read text/code answer OR transcribe audio ─────────────────────────
    if answer is not None:
        transcript = answer
        logger.info("Text answer received — session=%s chars=%d", session_id[:8], len(transcript))
    elif audio is not None:
        raw_bytes = await audio.read()
        filename = audio.filename or "recording.webm"
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
        logger.info(
            "Audio received — session=%s  bytes=%d  ext=%s",
            session_id[:8], len(raw_bytes), ext,
        )
        transcript = transcribe(raw_bytes, ext)
        logger.info("Transcript: %s…", transcript[:80])
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either audio file or answer text.",
        )

    normalized = (transcript or "").strip()
    is_skipped = normalized == "" or normalized.upper() == "SKIPPED"
    saved_answer = "SKIPPED" if is_skipped else normalized
    result_score: Optional[int] = None
    result_feedback = ""
    result_expected = None
    result_gap = None
    result_improvement = None
    result_explanation = None
    result_how_to_answer = None
    result_key_points: Optional[list[str]] = None
    result_example = None
    is_follow_up = False
    follow_up_reason = None

    if is_skipped:
        # Teaching mode: explicit educational payload for skipped/empty answers.
        result_score = 0
        result_feedback = "You skipped this - let's learn it."
        result_expected = (
            "A strong answer should define the concept clearly, describe trade-offs, "
            "and include one concrete project example with measurable impact."
        )
        result_explanation = (
            "Skipping prevents the interviewer from assessing your reasoning depth. "
            "Even a partial structured response demonstrates problem solving."
        )
        result_how_to_answer = (
            "Use STAR in 4 steps: context, your action, technical decision, and result."
        )
        result_key_points = [
            "Start with a crisp definition",
            "Explain design choices and trade-offs",
            "Give one real-world implementation example",
            "Close with measurable impact",
        ]
        result_example = (
            "In my last project, I built a feature store pipeline to reduce model-serving "
            "latency by 32 percent while keeping offline-online feature parity."
        )
        result_gap = "No answer provided, so technical depth and clarity could not be assessed."
        result_improvement = "Answer even if unsure; start with fundamentals and one practical example."
    else:
        if not llm_ready():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Gemini API is not configured. Set GEMINI_API_KEY to evaluate answers.",
            )

        history = _build_history(session)
        follow_up_depth = session.rounds[-1].follow_up_depth if session.rounds else 0
        step = generate_next_step(
            question=session.rounds[-1].question if session.rounds else "",
            answer=saved_answer,
            domain=session.role,
            history=history,
            follow_up_count=follow_up_depth,
        )
        result_score = step.score
        result_feedback = step.feedback
        result_expected = step.expected_answer
        result_gap = step.gap_analysis
        result_improvement = step.improvement
        is_follow_up = step.follow_up
        follow_up_reason = step.follow_up_reason

    # ── Persist and advance round counter ─────────────────────────────────
    # Capture pre-submit index so "last" means: this answer just completed final slot.
    round_before_submit = session.current_round
    record_answer(
        session_id,
        saved_answer,
        result_feedback,
        int(result_score or 0),
        expected_answer=result_expected,
        gap_analysis=result_gap,
        improvement=result_improvement,
        explanation=result_explanation,
        how_to_answer=result_how_to_answer,
        key_points=result_key_points,
        example=result_example,
    )

    completed_rounds = session.current_round
    is_last_answered = (round_before_submit + 1) == session.max_rounds
    is_complete      = completed_rounds >= session.max_rounds
    next_q: Optional[str] = None

    if not is_complete:
        if is_skipped:
            prev_qs = [r.question for r in session.rounds]
            prev_as = [r.answer if r.answer != "SKIPPED" else "[skipped]" for r in session.rounds]
            next_q, next_q_type = generate_next_question_payload(session.role, prev_qs, prev_as)
        else:
            next_q = step.next_question
            next_q_type = "coding" if "implement" in (next_q or "").lower() or "write" in (next_q or "").lower() else "text"
        add_question_v5(
            session_id      = session_id,
            question        = next_q,
            is_follow_up    = is_follow_up,
            follow_up_depth = (session.rounds[-1].follow_up_depth + 1) if is_follow_up else 0,
        )
    else:
        logger.info("Final answer processed — session=%s", session_id[:8])

    logger.info(
        "V5 submit — session=%s  score=%d  follow_up=%s  complete=%s",
        session_id[:8], int(result_score or 0), is_follow_up, is_complete,
    )

    return SubmitResponse(
        transcript       = saved_answer,
        feedback         = result_feedback,
        score            = result_score,
        expected_answer  = result_expected,
        gap_analysis     = result_gap,
        improvement_suggestion = result_improvement,
        explanation      = result_explanation,
        how_to_answer    = result_how_to_answer,
        key_points       = result_key_points,
        example          = result_example,
        next_question    = next_q,
        type             = next_q_type if not is_complete else "text",
        is_last          = is_last_answered,
        message          = "last question answered" if is_last_answered else None,
        is_complete      = is_complete,
        round_number     = completed_rounds,
        total_rounds     = session.max_rounds,
        follow_up        = is_follow_up,
        is_follow_up     = is_follow_up,
        follow_up_reason = follow_up_reason,
    )


@public_router.post("/submit-answer", response_model=SubmitResponse, summary="Submit answer (compat route)")
async def submit_answer_compat(
    request: Request,
    session_id: Optional[str] = Form(None, description="Session ID from /start"),
    audio: Optional[UploadFile] = File(None, description="Recorded audio (WebM/M4A/WAV)"),
    answer: Optional[str] = Form(None, description="Direct text/code answer"),
) -> SubmitResponse:
    return await submit_answer(request, session_id, audio, answer)


@router.post(
    "/skip-question",
    response_model = SkipResponse,
    summary        = "Skip the current question and move to the next",
)
async def skip_question(
    session_id: str = Form(..., description="Session ID from /start"),
) -> SkipResponse:
    """
    Mark the current open question as SKIPPED (score = 0).
    If rounds remain, generate and return the next question.
    If this was the last round, mark the session as completed.

    The frontend calls this when:
      - The user clicks \"Skip Question\"
      - The 15-second inactivity timer fires
    """
    session = _require_session(session_id)

    if session.status == "completed":
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "This interview session has already ended.",
        )
    if not session.rounds or session.rounds[-1].answer is not None:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "No open question to skip.",
        )

    # Mark current round as SKIPPED
    skip_round(session_id)
    logger.info("Question skipped — session=%s  round=%d", session_id[:8], session.current_round)

    completed_rounds = session.current_round
    is_complete      = completed_rounds >= session.max_rounds
    next_q: Optional[str] = None

    if not is_complete:
        # Exclude SKIPPED answers from context so LLM gets real Q&A only
        prev_qs = [r.question for r in session.rounds]
        prev_as = [r.answer if r.answer != "SKIPPED" else "[skipped]" for r in session.rounds]
        next_q, _ = generate_next_question_payload(session.role, prev_qs, prev_as)
        add_question(session_id, next_q)
    else:
        complete_session(session_id)

    return SkipResponse(
        skipped      = True,
        next_question = next_q,
        is_complete  = is_complete,
        round_number = completed_rounds,
        total_rounds = session.max_rounds,
    )


@router.post("/end", summary="Force-end a session and get final evaluation")
async def end_interview(
    session_id: str = Form(..., description="Session ID to end"),
) -> JSONResponse:
    """
    Generate a holistic evaluation based on all completed rounds.
    Can be called before all rounds are complete (user exits early).
    """
    session = _require_session(session_id)
    complete_session(session_id)

    result = build_final_report(session.rounds)

    logger.info(
        "Final evaluation — session=%s score=%s reviews=%d",
        session_id[:8], result.get("final_score"), len(result.get("question_reviews", [])),
    )
    return JSONResponse(content=result)


@public_router.post("/end-interview", summary="End interview (compat route)")
async def end_interview_compat(
    session_id: str = Form(..., description="Session ID to end"),
) -> JSONResponse:
    return await end_interview(session_id)


@router.get("/session/{session_id}", summary="Inspect session state (debug)")
async def get_session_state(session_id: str) -> Dict[str, Any]:
    """Return the full session transcript for debugging."""
    s = _require_session(session_id)
    return {
        "session_id":    s.session_id,
        "role":          s.role,
        "status":        s.status,
        "current_round": s.current_round,
        "max_rounds":    s.max_rounds,
        "rounds": [
            {
                "question": r.question,
                "answer":   r.answer,
                "feedback": r.feedback,
                "score":    r.score,
                "expected_answer": r.expected_answer,
                "explanation": r.explanation,
                "how_to_answer": r.how_to_answer,
                "key_points": r.key_points,
                "example": r.example,
            }
            for r in s.rounds
        ],
    }
