"""In-memory session manager for interview sessions.

Stores session state (questions, answers, scores, feedback) in memory. This is
intended for development and testing; persistence/DB can be added later.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, questions: List[str]) -> str:
        sid = str(uuid.uuid4())
        self._sessions[sid] = {
            "questions": list(questions),
            "answers": [],  # list of inference results
            "scores": [],
            "feedback": [],
            "created_at": time.time(),
            "current_q_idx": 0,
        }
        log.info("Created session %s with %d questions", sid, len(questions))
        return sid

    def get_current_question(self, session_id: str) -> Optional[str]:
        s = self._sessions.get(session_id)
        if not s:
            return None
        idx = s.get("current_q_idx", 0)
        questions = s.get("questions", [])
        if idx >= len(questions):
            return None
        return questions[idx]

    def add_answer(self, session_id: str, inference_result: Dict[str, Any]) -> None:
        s = self._sessions.get(session_id)
        if not s:
            log.error("Session not found: %s", session_id)
            return
        s["answers"].append(inference_result)
        s["scores"].append(inference_result.get("final_score", 0.0))
        s["feedback"].extend(inference_result.get("feedback", []))
        s["current_q_idx"] = min(len(s["questions"]), s.get("current_q_idx", 0) + 1)
        log.info("Session %s recorded answer; advanced to idx=%d", session_id, s["current_q_idx"])

    def end_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        s = self._sessions.get(session_id)
        if not s:
            log.error("Session not found: %s", session_id)
            return None
        summary = {
            "session_id": session_id,
            "created_at": s.get("created_at"),
            "num_questions": len(s.get("questions", [])),
            "num_answers": len(s.get("answers", [])),
            "mean_score": float(sum(s.get("scores", [])) / len(s.get("scores", []))) if s.get("scores") else 0.0,
            "feedback": list(dict.fromkeys(s.get("feedback", []))) , # dedupe preserving order
        }
        log.info("Ended session %s summary=%s", session_id, summary)
        return summary

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)


def test_session_manager() -> None:
    from interview_engine.question_generator import QuestionGenerator

    qm = QuestionGenerator()
    sm = SessionManager()
    sid = sm.create_session(qm.all_questions())
    assert sm.get_current_question(sid) == qm.all_questions()[0]
    log.info("Session manager test created %s", sid)


if __name__ == "__main__":
    test_session_manager()
