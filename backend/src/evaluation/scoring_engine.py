"""
scoring_engine.py
-----------------
Aggregates per-round NLP scores + CV scores into the final four metrics:

  technical_score     – how well answers addressed the questions (relevance + completeness)
  communication_score – how clearly the candidate expressed themselves (clarity + completeness)
  confidence_score    – composure, derived from CV signals or answer quality
  overall_score       – weighted composite

Weights for overall_score
~~~~~~~~~~~~~~~~~~~~~~~~~
  technical     40 %
  communication 35 %
  confidence    25 %
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional

from src.evaluation.cv_integrator import (
    compute_confidence_from_text,
    compute_confidence_score,
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

RoundAnalysis = Dict[str, object]   # output of nlp_analyzer.analyze_round


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------


def compute_scores(
    round_analyses:  List[RoundAnalysis],
    eye_contact_pct: Optional[float] = None,
    posture:         Optional[str]   = None,
    emotion:         Optional[str]   = None,
) -> Dict[str, int]:
    """
    Combine per-round NLP analyses and optional CV data into final scores.

    Parameters
    ----------
    round_analyses  : list of dicts from nlp_analyzer.analyze_round()
    eye_contact_pct : CV signal (0 – 100)
    posture         : "Good" | "Slouching" | "Leaning" | None
    emotion         : "Happy" | "Neutral" | "Sad" | "Angry" | "Surprise" | None

    Returns
    -------
    dict with keys:
      technical_score, communication_score, confidence_score, overall_score
    """
    if not round_analyses:
        return {
            "technical_score":     0,
            "communication_score": 0,
            "confidence_score":    0,
            "overall_score":       0,
        }

    # ── Per-round signal extraction ──────────────────────────────────────
    relevance_scores    = [int(r["relevance"])    for r in round_analyses]
    completeness_scores = [int(r["completeness"]) for r in round_analyses]
    clarity_scores      = [int(r["clarity"])      for r in round_analyses]

    # ── Dimension roll-ups ───────────────────────────────────────────────
    avg_relevance    = statistics.mean(relevance_scores)
    avg_completeness = statistics.mean(completeness_scores)
    avg_clarity      = statistics.mean(clarity_scores)

    # Technical  = does the candidate know *what* to say?
    # Weighted: relevance matters more than word count
    technical_score = int(round(avg_relevance * 0.65 + avg_completeness * 0.35))

    # Communication = does the candidate say it *well*?
    communication_score = int(round(avg_clarity * 0.55 + avg_completeness * 0.45))

    # Confidence = presence / composure
    cv_confidence = compute_confidence_score(eye_contact_pct, posture, emotion)
    if cv_confidence is not None:
        confidence_score = cv_confidence
    else:
        # Fallback: high technical + communication → likely composed
        confidence_score = compute_confidence_from_text(communication_score, technical_score)

    # Overall — intentionally heavier on substance than style
    overall_score = int(round(
        technical_score     * 0.40 +
        communication_score * 0.35 +
        confidence_score    * 0.25
    ))

    return {
        "technical_score":     min(100, max(0, technical_score)),
        "communication_score": min(100, max(0, communication_score)),
        "confidence_score":    min(100, max(0, confidence_score)),
        "overall_score":       min(100, max(0, overall_score)),
    }


def score_label(score: int) -> str:
    """Human-readable band label for a 0–100 score."""
    if score >= 85: return "Excellent"
    if score >= 70: return "Good"
    if score >= 55: return "Fair"
    if score >= 40: return "Needs Work"
    return "Poor"
