from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database import advanced_models
import logging

log = logging.getLogger(__name__)


def create_session(session_id: str, role: Optional[str] = None) -> advanced_models.AdvancedInterviewSession:
    db: Session = SessionLocal()
    try:
        s = advanced_models.AdvancedInterviewSession(session_id=session_id, role=role)
        db.add(s)
        db.commit()
        db.refresh(s)
        log.info("Created advanced session %s", session_id)
        return s
    finally:
        db.close()


def create_question(session_id: str, index: int, question_text: str) -> advanced_models.AdvancedInterviewQuestion:
    db: Session = SessionLocal()
    try:
        q = advanced_models.AdvancedInterviewQuestion(session_id=session_id, index=index, question_text=question_text)
        db.add(q)
        db.commit()
        db.refresh(q)
        log.info("Created question %d for session %s", q.id, session_id)
        return q
    finally:
        db.close()


def save_answer(session_id: str, question_id: int, score: float, emotion: float, posture: float, eye: float):
    db: Session = SessionLocal()
    try:
        a = advanced_models.AdvancedInterviewAnswer(session_id=session_id, question_id=question_id, score=float(score), emotion_score=float(emotion), posture_score=float(posture), eye_score=float(eye))
        db.add(a)
        db.commit()
        db.refresh(a)
        log.info("Saved advanced answer id=%d for session=%s", a.id, session_id)
        return a
    finally:
        db.close()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        s = db.query(advanced_models.AdvancedInterviewSession).filter_by(session_id=session_id).first()
        if not s:
            return None
        return {"session_id": s.session_id, "role": s.role, "created_at": s.created_at.isoformat()}
    finally:
        db.close()


def get_questions(session_id: str) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        qs = db.query(advanced_models.AdvancedInterviewQuestion).filter_by(session_id=session_id).order_by(advanced_models.AdvancedInterviewQuestion.index).all()
        return [{"id": q.id, "index": q.index, "question_text": q.question_text, "created_at": q.created_at.isoformat()} for q in qs]
    finally:
        db.close()


def get_answers(session_id: str) -> List[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        rows = db.query(advanced_models.AdvancedInterviewAnswer).filter_by(session_id=session_id).order_by(advanced_models.AdvancedInterviewAnswer.created_at).all()
        return [{"id": r.id, "question_id": r.question_id, "score": r.score, "emotion_score": r.emotion_score, "posture_score": r.posture_score, "eye_score": r.eye_score, "created_at": r.created_at.isoformat()} for r in rows]
    finally:
        db.close()
