from __future__ import annotations

import logging
import datetime
import json
from typing import Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from database.db import Base

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    answers = relationship("AnswerResult", back_populates="session")


class AnswerResult(Base):
    __tablename__ = "answer_results"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("interview_sessions.session_id"), index=True, nullable=False)
    question = Column(Text, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    feedback = Column(Text, nullable=True)  # JSON encoded list
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("InterviewSession", back_populates="answers")

    def set_feedback(self, fb_list: Optional[list]) -> None:
        try:
            self.feedback = json.dumps(fb_list or [])
        except Exception:
            self.feedback = json.dumps([])

    def get_feedback(self) -> list:
        try:
            return json.loads(self.feedback) if self.feedback else []
        except Exception:
            return []


class InterviewResult(Base):
    __tablename__ = "interview_results"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("interview_sessions.session_id"), index=True, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    emotion_score = Column(Float, nullable=False, default=0.0)
    posture_score = Column(Float, nullable=False, default=0.0)
    eye_contact_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("InterviewSession")



if __name__ == "__main__":
    from database.db import init_db

    init_db()
    log.info("Models created")
