from __future__ import annotations

import logging
import os
import concurrent.futures
from utils.logger import get_logger
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi import UploadFile, File
from pydantic import BaseModel
from uuid import uuid4

from interview_engine.interview_manager import InterviewManager
from database import crud
from database.crud import create_session, save_answer

from utils.storage_manager import save_video, generate_filename
from pipelines.async_pipeline import run_async

INFERENCE_TIMEOUT: int = int(os.getenv("AIIT_INFERENCE_TIMEOUT", "60"))

log = get_logger(__name__)

router = APIRouter()

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
    try:
        info = IM.start_interview()
        try:
            crud.create_session(info["session_id"])
        except Exception:
            log.exception("Failed to persist session in DB")
        return StartResponse(session_id=info["session_id"], first_question=info.get("first_question"))
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in start_interview: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/answer")
def submit_answer(req: AnswerRequest):
    try:
        session_id = req.session_id
        current_q = IM._sm.get_current_question(session_id)
        if current_q is None:
            raise HTTPException(status_code=404, detail="Session not found or no current question")

        try:
            sess = IM.process_answer(session_id, req.video_path)
        except Exception as exc:
            log.exception("Processing answer failed: %s", exc)
            raise HTTPException(status_code=500, detail="Processing failed")

        try:
            last_answer = sess.get("answers", [])[-1] if sess else None
            final_score = float(last_answer.get("final_score", 0.0)) if last_answer else 0.0
            feedback = last_answer.get("feedback", []) if last_answer else []
            crud.save_answer(session_id, current_q, final_score, feedback)
        except Exception:
            log.exception("Failed to persist answer to DB for session=%s", session_id)

        return {"status": "ok", "session": sess}
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in submit_answer: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/finish")
def finish_interview(req: FinishRequest):
    try:
        summary = IM.finish_interview(req.session_id)
        if summary is None:
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            db_summary = crud.get_session(req.session_id)
        except Exception:
            log.exception("Failed to fetch session from DB")
            db_summary = None
        return {"summary": summary, "db": db_summary}
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in finish_interview: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")



@router.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    try:
        try:
            content = await file.read()
        except Exception as exc:
            log.error("Failed to read uploaded file: %s", exc, exc_info=True)
            raise HTTPException(status_code=400, detail="Failed to read uploaded file")

        log.info("File uploaded: %s (%d bytes)", getattr(file, "filename", "<unknown>"), len(content) if content is not None else 0)

        name = generate_filename("mp4")
        try:
            saved_path = save_video(content, name)
        except Exception as exc:
            log.error("Failed to save uploaded file: %s", exc, exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")

        log.info("Saved file: %s", saved_path)

        try:
            result = run_async(str(saved_path))
        except Exception:
            log.exception("Async inference failed for %s", saved_path)
            result = {"emotion_score": 0.0, "eye_score": 0.0, "posture_score": 0.0, "final_score": 0.0, "feedback": []}

        log.info("Inference done for file: %s", saved_path)

        session_id = str(uuid4())
        try:
            create_session(session_id)
            log.info("Created DB session for upload: %s", session_id)
        except Exception as exc:
            log.error("Failed to create DB session for upload %s: %s", session_id, exc, exc_info=True)

        try:
            final_score = float(result.get("final_score", 0.0)) if isinstance(result, dict) else 0.0
            feedback = result.get("feedback", []) if isinstance(result, dict) else []
            save_answer(session_id, "upload", final_score, feedback)
            log.info("Saved upload answer for session=%s score=%.3f", session_id, final_score)
        except Exception as exc:
            log.error("Failed to save upload answer for session=%s: %s", session_id, exc, exc_info=True)

        return {"session_id": session_id, "result": result}
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in analyze_upload: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")



@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """Compatibility endpoint: accept uploads posted to /analyze and forward
    them to the existing /analyze/upload handler.
    """
    # Delegate to the existing implementation to avoid duplication.
    return await analyze_upload(file)
