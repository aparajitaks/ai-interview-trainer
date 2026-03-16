from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from typing import Optional

from database import session_crud
from interview_engine.question_generator import generate_question

log = logging.getLogger(__name__)
router = APIRouter()


class StartRequest(BaseModel):
    role: Optional[str] = None


class StartResponse(BaseModel):
    session_id: str
    question: str
    question_index: int
    question_id: int


class NextRequest(BaseModel):
    session_id: str


class AnswerRequest(BaseModel):
    session_id: str
    question_id: int
    score: float
    emotion_score: float
    posture_score: float
    eye_score: float


@router.post("/session/start", response_model=StartResponse)
def start_session(req: StartRequest):
    try:
        sid = str(uuid4())
        session_crud.create_session(sid, role=req.role)
        # generate first question
        qtext = generate_question(req.role or "", [])
        q = session_crud.create_question(sid, 1, qtext)
        return StartResponse(session_id=sid, question=qtext, question_index=1, question_id=q.id)
    except Exception as exc:
        log.exception("Failed to start session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to start session")


@router.post("/session/next")
def next_question(req: NextRequest):
    try:
        # determine how many questions exist and return next
        qs = session_crud.get_questions(req.session_id)
        history = [q["question_text"] for q in qs]
        if len(history) >= 5:
            return {"done": True}
        idx = len(history) + 1
        qtext = generate_question("", history)
        q = session_crud.create_question(req.session_id, idx, qtext)
        return {"done": False, "question": qtext, "question_index": idx, "question_id": q.id}
    except Exception as exc:
        log.exception("Failed to get next question: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get next question")


@router.post("/session/answer")
def submit_answer(req: AnswerRequest):
    try:
        session_crud.save_answer(req.session_id, req.question_id, req.score, req.emotion_score, req.posture_score, req.eye_score)
        return {"status": "ok"}
    except Exception as exc:
        log.exception("Failed to save answer: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save answer")


@router.post("/session/finish")
def finish_session(req: NextRequest):
    try:
        answers = session_crud.get_answers(req.session_id)
        if not answers:
            return {"summary": {"total_questions": 0}}
        total = len(answers)
        avg_score = sum(a["score"] for a in answers) / total if total else 0.0
        return {"summary": {"total_questions": total, "average_score": avg_score}, "answers": answers}
    except Exception as exc:
        log.exception("Failed to finish session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to finish session")
