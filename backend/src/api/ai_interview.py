from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.interview.session import (
    add_question_v5,
    get_current_follow_up_depth,
    get_session,
    record_answer,
)
from src.llm_engine import (
    RoundMemory,
    generate_next_step,
    is_ready as llm_ready,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["AI Interview V5"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AINextQuestionRequest(BaseModel):
    """Input for POST /ai-next-question."""
    session_id: str = Field(..., description="Active interview session ID")
    question:   str = Field(..., description="The question that was just asked")
    answer:     str = Field(..., description="The candidate's answer")
    domain:     str = Field(..., description="Job role / domain")


class AINextQuestionResponse(BaseModel):
    """Output from the V5 engine."""
    next_question:    str
    feedback:         str
    score:            int
    follow_up:        bool
    is_follow_up:     Optional[bool] = None
    your_answer:      str
    expected_answer:  str
    gap_analysis:     str
    improvement_suggestion: str
    follow_up_reason: Optional[str] = None
    round_number:     int
    total_rounds:     int
    is_complete:      bool


# ---------------------------------------------------------------------------
# Helper: convert session rounds to RoundMemory objects
# ---------------------------------------------------------------------------

def _build_history(session) -> list[RoundMemory]:
    """Convert session rounds to RoundMemory objects for the engine."""
    memories = []
    for r in session.rounds:
        if r.answer is not None:
            memories.append(RoundMemory(
                question        = r.question,
                answer          = r.answer,
                score           = r.score,
                feedback        = r.feedback,
                expected_answer = r.expected_answer,
                gap_analysis    = r.gap_analysis,
                improvement     = r.improvement,
                is_follow_up    = r.is_follow_up,
                follow_up_depth = r.follow_up_depth,
            ))
    return memories


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/ai-next-question",
    response_model = AINextQuestionResponse,
    summary        = "V5: Evaluate answer + generate next question with cross-questioning",
)
async def ai_next_question(body: AINextQuestionRequest) -> AINextQuestionResponse:
    """
    Evaluate the candidate's answer and generate the next question.

    Cross-questioning logic:
    - If score < 6 and < 2 follow-ups on this topic → ask a probing follow-up
    - Otherwise → move to a new topic

    The answer is recorded in the session and the next question is
    appended with follow-up metadata.
    """
    session = get_session(body.session_id)
    if session is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = f"Session '{body.session_id}' not found.",
        )

    if session.status == "completed":
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail      = "This interview session has already ended.",
        )

    answer_text = (body.answer or "").strip()
    is_skipped = answer_text == "" or answer_text.upper() == "SKIPPED"

    # Teaching mode for explicit skip/empty answer
    if is_skipped:
        record_answer(
            session_id=body.session_id,
            answer="SKIPPED",
            feedback="You skipped this - let's learn it.",
            score=0,
            expected_answer=(
                "A strong answer should define the core concept, explain trade-offs, "
                "and include one concrete implementation example with measurable impact."
            ),
            gap_analysis="No answer provided, so technical depth and clarity were not assessable.",
            improvement="Respond even if unsure. Start with fundamentals, then add one practical example.",
            explanation=(
                "Skipping prevents the interviewer from assessing your thinking process. "
                "A short structured answer is always better than silence."
            ),
            how_to_answer="Use STAR: context, action, decision rationale, and measurable result.",
            key_points=[
                "Define the concept clearly",
                "Show your approach and trade-offs",
                "Use one concrete example",
                "Close with impact",
            ],
            example="I improved API response time by redesigning caching, reducing p95 latency by 28%.",
        )
        completed_rounds = session.current_round
        is_complete = completed_rounds >= session.max_rounds
        next_q = "Let's continue. Tell me about a project where you solved a difficult technical problem."
        if not is_complete:
            add_question_v5(
                session_id=body.session_id,
                question=next_q,
                is_follow_up=False,
                follow_up_depth=0,
            )
        return AINextQuestionResponse(
            next_question=next_q,
            feedback="You skipped this - let's learn it.",
            score=0,
            follow_up=False,
            is_follow_up=False,
            your_answer="SKIPPED",
            expected_answer=(
                "A strong answer should define the core concept, explain trade-offs, "
                "and include one concrete implementation example with measurable impact."
            ),
            gap_analysis="No answer provided, so technical depth and clarity were not assessable.",
            improvement_suggestion="Respond even if unsure. Start with fundamentals, then add one practical example.",
            follow_up_reason=None,
            round_number=completed_rounds,
            total_rounds=session.max_rounds,
            is_complete=is_complete,
        )

    if not llm_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured. Set GEMINI_API_KEY to run interviewer evaluation.",
        )

    # Build conversation history for the engine
    history          = _build_history(session)
    follow_up_depth  = get_current_follow_up_depth(body.session_id)

    # Run the V5 engine
    result = generate_next_step(
        question        = body.question,
        answer          = answer_text,
        domain          = body.domain,
        history         = history,
        follow_up_count = follow_up_depth,
    )

    # Record the answer in the session
    record_answer(
        session_id = body.session_id,
        answer     = answer_text,
        feedback   = result.feedback,
        score      = result.score,
        expected_answer = result.expected_answer,
        gap_analysis = result.gap_analysis,
        improvement = result.improvement,
    )

    # Check completion
    completed_rounds = session.current_round
    is_complete      = completed_rounds >= session.max_rounds

    if not is_complete:
        # Determine new follow-up depth
        new_depth = (follow_up_depth + 1) if result.is_follow_up else 0

        add_question_v5(
            session_id      = body.session_id,
            question        = result.next_question,
            is_follow_up    = result.is_follow_up,
            follow_up_depth = new_depth,
        )

    logger.info(
        "V5 next-step — session=%s  score=%d  follow_up=%s  depth=%d  complete=%s",
        body.session_id[:8], result.score, result.is_follow_up,
        follow_up_depth, is_complete,
    )

    return AINextQuestionResponse(
        next_question    = result.next_question,
        feedback         = result.feedback,
        score            = result.score,
        follow_up        = result.follow_up,
        is_follow_up     = result.follow_up,
        your_answer      = answer_text,
        expected_answer  = result.expected_answer,
        gap_analysis     = result.gap_analysis,
        improvement_suggestion = result.improvement,
        follow_up_reason = result.follow_up_reason,
        round_number     = completed_rounds,
        total_rounds     = session.max_rounds,
        is_complete      = is_complete,
    )
