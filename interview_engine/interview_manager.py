"""Interview manager orchestrating questions and inference results.

This module ties together the question generator, session manager and the
inference pipeline. It stores results in memory via the SessionManager and
is intentionally synchronous and headless for easy testing.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Any, Optional

from interview_engine.question_generator import QuestionGenerator
from interview_engine.session_manager import SessionManager
from pipelines.inference_pipeline import run_inference
from config.settings import STORAGE_DIR, LOG_LEVEL

log = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


class InterviewManager:
    def __init__(self) -> None:
        self._qm = QuestionGenerator()
        self._sm = SessionManager()

    def start_interview(self) -> Dict[str, Any]:
        """Start a new interview session and return session info including first question."""
        questions = self._qm.all_questions()
        session_id = self._sm.create_session(questions)
        first_q = self._sm.get_current_question(session_id)
        log.info("Started interview session %s", session_id)
        return {"session_id": session_id, "first_question": first_q}

    def process_answer(self, session_id: str, video_path: str) -> Optional[Dict[str, Any]]:
        """Process an answer video: run inference, store results, and return updated session state."""
        # Run the inference pipeline
        log.info("Processing answer for session=%s video=%s", session_id, video_path)
        result = run_inference(video_path)

        # Persist into session
        self._sm.add_answer(session_id, result)

        # Return current session snapshot
        sess = self._sm.get_session(session_id)
        log.debug("Session %s after processing: %s", session_id, sess)
        return sess

    def finish_interview(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Finish interview and return summarized results."""
        summary = self._sm.end_session(session_id)
        log.info("Finished interview %s", session_id)
        return summary


def test_flow() -> None:
    """Simple demo flow that creates a session and shows the API usage.

    Replace `sample_video` with a real video path to run an end-to-end test.
    """
    im = InterviewManager()
    info = im.start_interview()
    sid = info["session_id"]
    log.info("Started session: %s; first question: %s", sid, info.get("first_question"))

    # NOTE: For a real run replace the sample path below with a real video.
    sample_video = os.path.join(STORAGE_DIR, "sample.mp4")
    # The following will run the inference pipeline which may download models.
    try:
        im.process_answer(sid, sample_video)
    except Exception:
        log.exception("process_answer demo failed (expected if sample video missing)")

    summary = im.finish_interview(sid)
    log.info("Demo summary: %s", summary)


if __name__ == "__main__":
    test_flow()
