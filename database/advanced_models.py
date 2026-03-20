from __future__ import annotations

import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship

from database.db import Base


class AdvancedInterviewSession(Base):
    __tablename__ = "adv_interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True, nullable=False)
    role = Column(String(64), nullable=True)
    # optional link to the authenticated user who started the session
    user_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    questions = relationship("AdvancedInterviewQuestion", back_populates="session")


class AdvancedInterviewQuestion(Base):
    __tablename__ = "adv_interview_questions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), ForeignKey("adv_interview_sessions.session_id"), index=True, nullable=False)
    question_text = Column(Text, nullable=False)
    index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("AdvancedInterviewSession", back_populates="questions")


class AdvancedInterviewAnswer(Base):
    __tablename__ = "adv_interview_answers"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    question_id = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    emotion_score = Column(Float, nullable=False, default=0.0)
    posture_score = Column(Float, nullable=False, default=0.0)
    eye_score = Column(Float, nullable=False, default=0.0)
    # store raw answer text (optional) and detected keywords
    answer_text = Column(Text, nullable=True)
    keywords = Column(Text, nullable=True)
    # LLM-generated feedback stored as JSON list (strings)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
