"""
session.py
----------
In-memory interview session store.

Stores all sessions in a module-level dict — no DB required for MVP.
Each session tracks the full Q&A transcript, per-round scores, and status.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Round:
    """One question–answer pair in an interview session."""
    question:        str
    answer:          Optional[str] = None
    feedback:        Optional[str] = None
    expected_answer: Optional[str] = None
    explanation:     Optional[str] = None
    how_to_answer:   Optional[str] = None
    key_points:      Optional[List[str]] = None
    example:         Optional[str] = None
    gap_analysis:    Optional[str] = None
    improvement:     Optional[str] = None
    score:           Optional[int] = None   # 1–10
    is_follow_up:    bool          = False   # V5: cross-questioning marker
    follow_up_depth: int           = 0      # V5: 0=new topic, 1=first follow-up, 2=max


@dataclass
class InterviewSession:
    """Full state of a live interview session."""
    session_id:    str
    role:          str
    rounds:        List[Round]       = field(default_factory=list)
    current_round: int               = 0      # rounds submitted so far
    max_rounds:    int               = 5
    created_at:    datetime          = field(default_factory=datetime.now)
    status:        str               = "active"   # "active" | "completed"


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_sessions: Dict[str, InterviewSession] = {}


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


def create_session(role: str, max_rounds: int = 5) -> InterviewSession:
    """Create and persist a new session, return it."""
    session = InterviewSession(
        session_id = str(uuid.uuid4()),
        role       = role,
        max_rounds = max_rounds,
    )
    _sessions[session.session_id] = session
    return session


def get_session(session_id: str) -> Optional[InterviewSession]:
    """Retrieve a session by ID, or None if not found."""
    return _sessions.get(session_id)


def add_question(session_id: str, question: str) -> None:
    """Append a new round with the given question (answer not yet recorded)."""
    s = _sessions.get(session_id)
    if s:
        s.rounds.append(Round(question=question))


def add_question_v5(
    session_id:      str,
    question:        str,
    is_follow_up:    bool = False,
    follow_up_depth: int  = 0,
) -> None:
    """V5: Append a round with cross-questioning metadata."""
    s = _sessions.get(session_id)
    if s:
        s.rounds.append(Round(
            question        = question,
            is_follow_up    = is_follow_up,
            follow_up_depth = follow_up_depth,
        ))


def record_answer(
    session_id: str,
    answer:     str,
    feedback:   str,
    score:      int,
    expected_answer: Optional[str] = None,
    gap_analysis: Optional[str] = None,
    improvement: Optional[str] = None,
    explanation: Optional[str] = None,
    how_to_answer: Optional[str] = None,
    key_points: Optional[List[str]] = None,
    example: Optional[str] = None,
) -> None:
    """Fill in the answer / feedback / score for the latest open round."""
    s = _sessions.get(session_id)
    if s and s.rounds:
        r          = s.rounds[-1]
        r.answer   = answer
        r.feedback = feedback
        r.expected_answer = expected_answer
        r.explanation = explanation
        r.how_to_answer = how_to_answer
        r.key_points = key_points
        r.example = example
        r.gap_analysis = gap_analysis
        r.improvement = improvement
        r.score    = score
        s.current_round += 1


def skip_round(session_id: str) -> None:
    """Mark the current open round as SKIPPED (score = 0, answer = 'SKIPPED')."""
    s = _sessions.get(session_id)
    if s and s.rounds:
        r          = s.rounds[-1]
        r.answer   = "SKIPPED"
        r.feedback = "You skipped this - let's learn it."
        r.expected_answer = (
            "A strong answer should define the concept clearly, discuss trade-offs, "
            "and include one practical example with measurable impact."
        )
        r.explanation = (
            "Skipping means your technical reasoning cannot be evaluated. "
            "A short structured attempt is always better than no response."
        )
        r.how_to_answer = "Use STAR: context, action, technical decision, and measurable result."
        r.key_points = [
            "Start with a concise definition",
            "Describe your approach and trade-offs",
            "Share one concrete project example",
            "Finish with quantified impact",
        ]
        r.example = "I redesigned a caching layer and reduced p95 latency by 28 percent."
        r.gap_analysis = "No answer provided, so relevance, completeness, and clarity were not measurable."
        r.improvement = "Answer even if unsure. Start from fundamentals and add one concrete example."
        r.score    = 0
        s.current_round += 1


def complete_session(session_id: str) -> None:
    """Mark a session as completed."""
    s = _sessions.get(session_id)
    if s:
        s.status = "completed"


def get_current_follow_up_depth(session_id: str) -> int:
    """
    V5: Return the current follow-up chain depth.

    Counts how many consecutive follow-up rounds are at the tail
    of the session. Returns 0 if the last question was a new topic.
    """
    s = _sessions.get(session_id)
    if not s or not s.rounds:
        return 0

    depth = 0
    for r in reversed(s.rounds):
        if r.is_follow_up:
            depth += 1
        else:
            break
    return depth

