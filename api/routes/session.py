from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from typing import Optional
from pathlib import Path
import tempfile
from config.settings import STORAGE_DIR

try:
    from audio_models.whisper_model import WhisperModel
except Exception:
    WhisperModel = None

try:
    from interview_engine.keyword_detector import detect_keywords, strength_from_answer
except Exception:
    detect_keywords = None
    strength_from_answer = None

from database import session_crud
from auth.jwt_handler import get_current_user
from fastapi import Depends
from interview_engine.question_generator import generate_question
try:
    from evaluation.llm_feedback import get_generator
except Exception:
    get_generator = None
from database import crud as dbcrud

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
    answer_text: Optional[str] = None
    video_path: Optional[str] = None


@router.post("/session/start", response_model=StartResponse)
def start_session(req: StartRequest, current_user: dict = Depends(get_current_user)):
    try:
        sid = str(uuid4())
        # associate session with the authenticated user
        uid = None
        if isinstance(current_user, dict):
            uid = current_user.get("id")
        session_crud.create_session(sid, role=req.role, user_id=str(uid) if uid is not None else None)
        # generate first question
        qtext = generate_question(req.role or "", [])
        q = session_crud.create_question(sid, 1, qtext)
        return StartResponse(session_id=sid, question=qtext, question_index=1, question_id=q.id)
    except Exception as exc:
        log.exception("Failed to start session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to start session")


@router.post("/session/next")
def next_question(req: NextRequest, current_user: dict = Depends(get_current_user)):
    try:
        # determine how many questions exist and return next
        qs = session_crud.get_questions(req.session_id)
        history = [q["question_text"] for q in qs]
        if len(history) >= 5:
            return {"done": True}
        idx = len(history) + 1
        # Try to get role and last answer text to drive adaptive generation
        sess = session_crud.get_session(req.session_id) or {}
        role = sess.get("role") if isinstance(sess, dict) else None
        answers = session_crud.get_answers(req.session_id)
        last_answer_text = None
        if answers:
            last = answers[-1]
            last_answer_text = last.get("answer_text")
        # compute detected keywords and strength for the last answer (if any)
        detected_keywords = None
        difficulty = None
        if last_answer_text:
            try:
                if detect_keywords:
                    try:
                        # prefer stored keywords from DB, otherwise detect
                        detected_keywords = last.get("keywords") if last.get("keywords") is not None else detect_keywords(role or "", last_answer_text)
                    except Exception:
                        detected_keywords = detect_keywords(role or "", last_answer_text)
            except Exception:
                log.exception("Keyword detection failed for next_question, session=%s", req.session_id)
            try:
                if strength_from_answer:
                    difficulty_map = {"weak": "easy", "medium": "medium", "strong": "hard"}
                    s = strength_from_answer(last_answer_text, detected_keywords or [])
                    difficulty = difficulty_map.get(s, None)
            except Exception:
                log.exception("Strength detection failed for next_question, session=%s", req.session_id)

        qtext = generate_question(role or "", history, last_answer_text, difficulty=difficulty, keywords=detected_keywords)
        q = session_crud.create_question(req.session_id, idx, qtext)
        return {"done": False, "question": qtext, "question_index": idx, "question_id": q.id}
    except Exception as exc:
        log.exception("Failed to get next question: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to get next question")


@router.post("/session/answer")
def submit_answer(req: AnswerRequest, current_user: dict = Depends(get_current_user)):
    try:
        # If client didn't provide answer_text but provided a video, try to
        # extract audio and run Whisper transcription.
        final_text = req.answer_text
        detected = None

        # Determine role for keyword detection context
        sess_meta = session_crud.get_session(req.session_id) or {}
        role = sess_meta.get("role") if isinstance(sess_meta, dict) else None

        if not final_text and req.video_path:
            try:
                # Extract audio using the existing preprocessing helper
                from preprocessing.audio_extract import extract_audio
                from utils.storage_manager import get_storage_dir, generate_filename

                storage_dir = get_storage_dir()
                # generate a wav filename and place it in storage dir
                wav_name = generate_filename("wav")
                wav_path = storage_dir / wav_name

                extract_audio(str(req.video_path), str(wav_path))

                if WhisperModel is not None:
                    wm = WhisperModel()
                    tr = wm.transcribe(str(wav_path))
                    final_text = tr.get("text") if isinstance(tr, dict) else None
                else:
                    # Whisper not available — leave final_text None
                    final_text = None
            except Exception:
                log.exception("Transcription attempt failed for session=%s", req.session_id)

        # Run simple keyword detection if we have text
        if final_text and detect_keywords:
            try:
                detected = detect_keywords(role or "", final_text)
            except Exception:
                log.exception("Keyword detection failed for session=%s", req.session_id)

        # Persist answer with optional text and detected keywords
        session_crud.save_answer(req.session_id, req.question_id, req.score, req.emotion_score, req.posture_score, req.eye_score, answer_text=final_text, keywords=detected)
        return {"status": "ok", "transcription": final_text, "keywords": detected}
    except Exception as exc:
        log.exception("Failed to save answer: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save answer")


@router.post("/session/finish")
def finish_session(req: NextRequest, current_user: dict = Depends(get_current_user)):
    try:
        answers = session_crud.get_answers(req.session_id)
        if not answers:
            return {"summary": {"total_questions": 0}}
        total = len(answers)
        avg_score = sum(a["score"] for a in answers) / total if total else 0.0
        # Attempt to generate LLM feedback for each answer if not already present
        role = None
        try:
            sess_meta = session_crud.get_session(req.session_id) or {}
            role = sess_meta.get("role") if isinstance(sess_meta, dict) else None
        except Exception:
            role = None

        if get_generator is not None:
            try:
                gen = get_generator()
                for a in answers:
                    if a.get("feedback"):
                        continue
                    try:
                        fb = gen.generate_feedback(role, a)
                        # Persist feedback to DB (save_feedback will JSON-encode)
                        try:
                            session_crud.save_feedback(a["id"], fb)
                        except Exception:
                            # If saving fails, still attach to response
                            pass
                        a["feedback"] = fb
                    except Exception:
                        log.exception("Failed to generate feedback for answer id=%s", a.get("id"))
            except Exception:
                log.exception("Failed to initialize feedback generator")

        return {"summary": {"total_questions": total, "average_score": avg_score}, "answers": answers}
    except Exception as exc:
        log.exception("Failed to finish session: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to finish session")


@router.get("/session/history")
def list_session_history():
    try:
        try:
            rows = session_crud.list_sessions()
        except Exception:
            log.exception("Failed to read session history from DB")
            raise HTTPException(status_code=500, detail="DB read failed")
        return rows
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in list_session_history: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/session/{session_id}")
def get_session_detail(session_id: str):
    try:
        try:
            s = session_crud.get_session_detail(session_id)
        except Exception:
            log.exception("Failed to read session detail from DB: %s", session_id)
            raise HTTPException(status_code=500, detail="DB read failed")
        if s is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return s
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in get_session_detail: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/session/stats")
def get_session_stats():
    try:
        try:
            s = dbcrud.get_stats()
        except Exception:
            log.exception("Failed to compute stats from DB")
            raise HTTPException(status_code=500, detail="DB read failed")
        return s
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in get_session_stats: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
