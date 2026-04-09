"""
evaluator.py
------------
Main orchestrator for the V4 Evaluation Engine.

Data flow
~~~~~~~~~
  session_id
      ↓
  Load InterviewSession (questions + answers from session store)
      ↓
  NLP analysis per round  (nlp_analyzer.analyze_round)
      ↓
  Scoring Engine          (scoring_engine.compute_scores)
      ↓
  Feedback Generator      (feedback_generator.generate_feedback)
      ↓
  EvaluationResult

Design decisions
~~~~~~~~~~~~~~~~
* The evaluation is purely additive — it does NOT replace the existing
  LLM-based /interview/end endpoint; it runs alongside it.
* CV data (eye_contact, posture, emotion) is optional.  When present it
  enriches the confidence_score; when absent the engine falls back to
  text-derived confidence.
* All logic is synchronous and CPU-bound — no await / async needed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.evaluation.nlp_analyzer       import analyze_round
from src.evaluation.scoring_engine     import compute_scores, score_label
from src.evaluation.feedback_generator import generate_feedback, generate_round_feedback
from src.interview.session             import get_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class RoundResult:
    question:        str
    answer:          str
    relevance:       int
    completeness:    int
    clarity:         int
    round_feedback:  str


@dataclass
class EvaluationResult:
    session_id:          str
    role:                str
    technical_score:     int
    communication_score: int
    confidence_score:    int
    overall_score:       int
    overall_label:       str
    feedback:            str
    rounds:              List[RoundResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id":          self.session_id,
            "role":                self.role,
            "technical_score":     self.technical_score,
            "communication_score": self.communication_score,
            "confidence_score":    self.confidence_score,
            "overall_score":       self.overall_score,
            "overall_label":       self.overall_label,
            "feedback":            self.feedback,
            "rounds": [
                {
                    "question":       r.question,
                    "answer":         r.answer,
                    "relevance":      r.relevance,
                    "completeness":   r.completeness,
                    "clarity":        r.clarity,
                    "round_feedback": r.round_feedback,
                }
                for r in self.rounds
            ],
        }


# ---------------------------------------------------------------------------
# Main evaluation function
# ---------------------------------------------------------------------------


def _is_skipped_or_empty(answer: Optional[str]) -> bool:
    """Return True if the answer should be treated as unanswered."""
    if not answer:
        return True
    stripped = answer.strip()
    return stripped == "" or stripped.upper() == "SKIPPED"


def evaluate_session(
    session_id:      str,
    eye_contact_pct: Optional[float] = None,
    posture:         Optional[str]   = None,
    emotion:         Optional[str]   = None,
) -> EvaluationResult:
    """
    Run the full evaluation pipeline for a completed interview session.

    Parameters
    ----------
    session_id      : interview session UUID
    eye_contact_pct : optional CV signal from video analysis (0–100)
    posture         : optional CV signal — "Good" | "Slouching" | "Leaning"
    emotion         : optional CV signal — "Happy" | "Neutral" | …

    Returns
    -------
    EvaluationResult

    Raises
    ------
    ValueError  if session_id is not found.
    """
    session = get_session(session_id)
    if session is None:
        raise ValueError(f"Session '{session_id}' not found.")

    # Classify every round that has *some* answer recorded
    answered = [r for r in session.rounds if r.answer is not None]
    if not answered:
        raise ValueError(
            f"Session '{session_id}' has no recorded answers yet. "
            "Complete at least one round before evaluating."
        )

    # Separate real answers from skipped / empty ones
    real_rounds   = [r for r in answered if not _is_skipped_or_empty(r.answer)]
    skipped_rounds = [r for r in answered if _is_skipped_or_empty(r.answer)]

    if skipped_rounds:
        logger.info(
            "Session %s: %d skipped/empty round(s) — scores zeroed for those rounds.",
            session_id[:8], len(skipped_rounds),
        )

    logger.info(
        "Evaluating session=%s  role='%s'  total=%d  answered=%d  skipped=%d",
        session_id[:8], session.role, len(answered),
        len(real_rounds), len(skipped_rounds),
    )

    # ── Per-round NLP analysis (only for real answers) ────────────────────
    round_analyses: List[Dict] = []
    round_results:  List[RoundResult] = []

    # Add skipped rounds as zero-score entries first
    for r in skipped_rounds:
        round_results.append(RoundResult(
            question       = r.question,
            answer         = r.answer or "",
            relevance      = 0,
            completeness   = 0,
            clarity        = 0,
            round_feedback = "Question was skipped — no score awarded.",
        ))

    for r in real_rounds:
        analysis = analyze_round(r.question, r.answer)
        round_analyses.append(analysis)

        rf = generate_round_feedback(
            relevance    = int(analysis["relevance"]),
            completeness = int(analysis["completeness"]),
            clarity      = int(analysis["clarity"]),
        )

        round_results.append(RoundResult(
            question       = r.question,
            answer         = r.answer,
            relevance      = int(analysis["relevance"]),
            completeness   = int(analysis["completeness"]),
            clarity        = int(analysis["clarity"]),
            round_feedback = rf,
        ))

        logger.debug(
            "  Round: rel=%d  comp=%d  clar=%d  → %s",
            analysis["relevance"], analysis["completeness"],
            analysis["clarity"], rf,
        )

    # ── Handle all-skipped case ───────────────────────────────────────────
    if not real_rounds:
        # Confidence can still come from CV if available
        from src.evaluation.cv_integrator import compute_confidence_score
        cv_confidence = compute_confidence_score(eye_contact_pct, posture, emotion)

        logger.info("All rounds skipped — returning zero scores.")
        return EvaluationResult(
            session_id          = session_id,
            role                = session.role,
            technical_score     = 0,
            communication_score = 0,
            confidence_score    = cv_confidence or 0,
            overall_score       = 0,
            overall_label       = score_label(0),
            feedback            = (
                "All questions were skipped — no evaluation is possible. "
                "Try answering at least a few questions to receive meaningful feedback."
            ),
            rounds              = round_results,
        )

    # ── Aggregate scores ───────────────────────────────────────────────────
    scores = compute_scores(round_analyses, eye_contact_pct, posture, emotion)

    # Apply skip penalty: scale scores down proportionally to answer rate
    answer_rate = len(real_rounds) / len(answered)
    if answer_rate < 1.0:
        logger.info("Applying skip penalty — answer rate %.0f%%", answer_rate * 100)
        scores["technical_score"]     = int(round(scores["technical_score"]     * answer_rate))
        scores["communication_score"] = int(round(scores["communication_score"] * answer_rate))
        # Confidence is less affected — only 50% penalty
        scores["confidence_score"]    = int(round(scores["confidence_score"] * (0.5 + 0.5 * answer_rate)))
        scores["overall_score"]       = int(round(
            scores["technical_score"]     * 0.40 +
            scores["communication_score"] * 0.35 +
            scores["confidence_score"]    * 0.25
        ))

    logger.info(
        "Scores — technical=%d  communication=%d  confidence=%d  overall=%d",
        scores["technical_score"], scores["communication_score"],
        scores["confidence_score"], scores["overall_score"],
    )

    # ── Human-like feedback ────────────────────────────────────────────────
    feedback = generate_feedback(scores, round_analyses)

    return EvaluationResult(
        session_id          = session_id,
        role                = session.role,
        technical_score     = scores["technical_score"],
        communication_score = scores["communication_score"],
        confidence_score    = scores["confidence_score"],
        overall_score       = scores["overall_score"],
        overall_label       = score_label(scores["overall_score"]),
        feedback            = feedback,
        rounds              = round_results,
    )
