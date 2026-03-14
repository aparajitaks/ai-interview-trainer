"""Routes to control interview lifecycle: start, answer, finish."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from interview_engine.interview_manager import InterviewManager
from database import crud

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# One InterviewManager instance for the app process
IM = InterviewManager()


class StartResponse(BaseModel):
    session_id: str
    first_question: Optional[str]


class AnswerRequest(BaseModel):
    session_id: str
    video_path: str


class FinishRequest(BaseModel):
    session_id: str


@router.post("/start", response_model=StartResponse)
def start_interview():
    info = IM.start_interview()
    # Persist session in DB
    try:
        crud.create_session(info["session_id"])
    except Exception:
        log.exception("Failed to persist session in DB")
    return StartResponse(session_id=info["session_id"], first_question=info.get("first_question"))


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    # Get current question before processing so we can persist the question text
    session_id = req.session_id
    current_q = IM._sm.get_current_question(session_id)
    if current_q is None:
        raise HTTPException(status_code=404, detail="Session not found or no current question")

    # Process the video (runs inference and stores in session manager)
    try:
        sess = IM.process_answer(session_id, req.video_path)
    except Exception as exc:
        log.exception("Processing answer failed: %s", exc)
        raise HTTPException(status_code=500, detail="Processing failed")

    # Persist the answer into DB
    try:
        # inference result is last appended answer
        last_answer = sess.get("answers", [])[-1] if sess else None
        final_score = float(last_answer.get("final_score", 0.0)) if last_answer else 0.0
        feedback = last_answer.get("feedback", []) if last_answer else []
        crud.save_answer(session_id, current_q, final_score, feedback)
    except Exception:
        log.exception("Failed to persist answer to DB for session=%s", session_id)

    return {"status": "ok", "session": sess}


@router.post("/finish")
def finish_interview(req: FinishRequest):
    summary = IM.finish_interview(req.session_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Optionally return stored DB representation
    try:
        db_summary = crud.get_session(req.session_id)
    except Exception:
        log.exception("Failed to fetch session from DB")
        db_summary = None
    return {"summary": summary, "db": db_summary}
