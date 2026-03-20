from __future__ import annotations

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database import advanced_models
import logging

log = logging.getLogger(__name__)


def create_session(session_id: str, role: Optional[str] = None, user_id: Optional[str] = None) -> advanced_models.AdvancedInterviewSession:
    db: Session = SessionLocal()
    try:
        # If session already exists, return it (idempotent create)
        s = db.query(advanced_models.AdvancedInterviewSession).filter_by(session_id=session_id).first()
        if s:
            log.info("Session %s already exists - returning existing", session_id)
            return s
        s = advanced_models.AdvancedInterviewSession(session_id=session_id, role=role, user_id=user_id)
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


def save_answer(session_id: str, question_id: int, score: float, emotion: float, posture: float, eye: float, answer_text: str | None = None, keywords: list | None = None):
    db: Session = SessionLocal()
    try:
        kws = None
        try:
            import json
            kws = json.dumps(keywords or [])
        except Exception:
            kws = None

        a = advanced_models.AdvancedInterviewAnswer(
            session_id=session_id,
            question_id=question_id,
            score=float(score),
            emotion_score=float(emotion),
            posture_score=float(posture),
            eye_score=float(eye),
            answer_text=answer_text,
            keywords=kws,
        )
        db.add(a)
        db.commit()
        db.refresh(a)
        log.info("Saved advanced answer id=%d for session=%s", a.id, session_id)
        return a
    finally:
        db.close()


def save_feedback(answer_id: int, feedback: list) -> advanced_models.AdvancedInterviewAnswer:
    """Persist LLM-generated feedback (list of strings) for a given answer row."""
    db: Session = SessionLocal()
    try:
        a = db.query(advanced_models.AdvancedInterviewAnswer).filter_by(id=answer_id).first()
        if not a:
            raise ValueError(f"Answer id={answer_id} not found")
        try:
            import json

            a.feedback = json.dumps(feedback or [])
        except Exception:
            a.feedback = None
        db.add(a)
        db.commit()
        db.refresh(a)
        log.info("Saved feedback for answer id=%d", a.id)
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
        out = []
        import json
        for r in rows:
            kws = []
            try:
                kws = json.loads(r.keywords) if r.keywords else []
            except Exception:
                kws = []
            out.append({
                "id": r.id,
                "question_id": r.question_id,
                "score": r.score,
                "emotion_score": r.emotion_score,
                "posture_score": r.posture_score,
                "eye_score": r.eye_score,
                "answer_text": r.answer_text,
            "keywords": kws,
            "feedback": (json.loads(r.feedback) if r.feedback else None) if isinstance(getattr(r, 'feedback', None), (str, bytes)) else r.feedback,
                "created_at": r.created_at.isoformat(),
            })
        return out
    finally:
        db.close()


def list_sessions(limit: int = 100, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return recent advanced interview sessions with simple aggregates.

    If user_id is provided, only sessions belonging to that user are returned.
    """
    db: Session = SessionLocal()
    try:
        q = db.query(advanced_models.AdvancedInterviewSession)
        if user_id is not None:
            q = q.filter_by(user_id=str(user_id))
        rows = q.order_by(advanced_models.AdvancedInterviewSession.created_at.desc()).limit(limit).all()
        out = []
        for r in rows:
            # compute average score for this session from answers
            answers = db.query(advanced_models.AdvancedInterviewAnswer).filter_by(session_id=r.session_id).all()
            avg = 0.0
            if answers:
                try:
                    avg = sum([a.score for a in answers]) / len(answers)
                except Exception:
                    avg = 0.0
            out.append({
                "session_id": r.session_id,
                "role": r.role,
                "average_score": float(avg),
                "created_at": r.created_at.isoformat(),
            })
        return out
    finally:
        db.close()


def get_session_detail(session_id: str) -> Optional[Dict[str, Any]]:
    """Return full session details: questions, answers, and aggregates."""
    db: Session = SessionLocal()
    try:
        s = db.query(advanced_models.AdvancedInterviewSession).filter_by(session_id=session_id).first()
        if not s:
            return None
        questions = db.query(advanced_models.AdvancedInterviewQuestion).filter_by(session_id=session_id).order_by(advanced_models.AdvancedInterviewQuestion.index).all()
        answers = db.query(advanced_models.AdvancedInterviewAnswer).filter_by(session_id=session_id).order_by(advanced_models.AdvancedInterviewAnswer.created_at).all()

        qlist = [{"id": q.id, "index": q.index, "question_text": q.question_text, "created_at": q.created_at.isoformat()} for q in questions]

        import json
        alist = []
        for a in answers:
            kws = []
            try:
                kws = json.loads(a.keywords) if a.keywords else []
            except Exception:
                kws = []
            fb = None
            try:
                fb = json.loads(a.feedback) if a.feedback else None
            except Exception:
                fb = a.feedback
            alist.append({
                "id": a.id,
                "question_id": a.question_id,
                "score": a.score,
                "emotion_score": a.emotion_score,
                "posture_score": a.posture_score,
                "eye_score": a.eye_score,
                "answer_text": a.answer_text,
                "keywords": kws,
                "feedback": fb,
                "created_at": a.created_at.isoformat(),
            })

        avg = 0.0
        if alist:
            try:
                avg = sum([a["score"] for a in alist]) / len(alist)
            except Exception:
                avg = 0.0

        return {
            "session_id": s.session_id,
            "role": s.role,
            "created_at": s.created_at.isoformat(),
            "questions": qlist,
            "answers": alist,
            "average_score": float(avg),
        }
    finally:
        db.close()
