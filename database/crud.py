"""CRUD helpers for the AI Interview Trainer database.

Provides simple wrappers around SQLAlchemy sessions to create sessions and
store/retrieve answer results. Designed for synchronous use in the app and
for testing.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
import json

from sqlalchemy.orm import Session

from database.db import SessionLocal, init_db
from database import models

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_session(session_id: str) -> models.InterviewSession:
    """Create and persist a new InterviewSession with the provided session_id."""
    db: Session = SessionLocal()
    try:
        s = models.InterviewSession(session_id=session_id)
        db.add(s)
        db.commit()
        db.refresh(s)
        log.info("Created DB session: %s", session_id)
        return s
    finally:
        db.close()


def save_answer(session_id: str, question: Optional[str], score: float, feedback: Optional[List[str]] = None) -> models.AnswerResult:
    """Persist a single answer result tied to a session_id."""
    db: Session = SessionLocal()
    try:
        # Ensure session exists
        sess = db.query(models.InterviewSession).filter_by(session_id=session_id).first()
        if not sess:
            log.info("DB session %s not found - creating", session_id)
            sess = create_session(session_id)

        ar = models.AnswerResult(session_id=session_id, question=question, score=float(score))
        ar.set_feedback(feedback or [])
        db.add(ar)
        db.commit()
        db.refresh(ar)
        log.info("Saved answer for session=%s id=%d", session_id, ar.id)
        return ar
    finally:
        db.close()


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Return session metadata and basic aggregates."""
    db: Session = SessionLocal()
    try:
        sess = db.query(models.InterviewSession).filter_by(session_id=session_id).first()
        if not sess:
            return None
        answers = db.query(models.AnswerResult).filter_by(session_id=session_id).all()
        results = [
            {"question": a.question, "score": a.score, "feedback": a.get_feedback(), "created_at": a.created_at.isoformat()} for a in answers
        ]
        return {"session_id": sess.session_id, "created_at": sess.created_at.isoformat(), "answers": results}
    finally:
        db.close()


def get_results(session_id: str) -> List[Dict[str, Any]]:
    """Return raw answer rows for a given session_id."""
    db: Session = SessionLocal()
    try:
        answers = db.query(models.AnswerResult).filter_by(session_id=session_id).all()
        return [
            {"id": a.id, "question": a.question, "score": a.score, "feedback": a.get_feedback(), "created_at": a.created_at.isoformat()} for a in answers
        ]
    finally:
        db.close()


def test_db_flow() -> None:
    """Headless test: initialize DB, create a session, save an answer, and query."""
    init_db()
    sid = "test-session-123"
    create_session(sid)
    save_answer(sid, "Tell me about yourself", 0.78, ["Maintain eye contact"]) 
    s = get_session(sid)
    log.info("Test session retrieved: %s", s)


if __name__ == "__main__":
    test_db_flow()
