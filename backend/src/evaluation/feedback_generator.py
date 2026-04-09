"""
feedback_generator.py
---------------------
Generates human-like, actionable feedback from evaluation scores and
per-round NLP observations.

Design philosophy
~~~~~~~~~~~~~~~~~
Feedback should feel like it came from a thoughtful interviewer, not a
rubric. We:
  1. Pick a tone-appropriate opening sentence.
  2. Surface the top strength and the most important improvement area.
  3. Add round-specific observations for specificity.
  4. Close with an encouraging, forward-looking statement.

No external API needed — entirely rule-based template composition.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Template banks
# ---------------------------------------------------------------------------

_OPENING_EXCELLENT = [
    "Outstanding performance across the board.",
    "Excellent interview — you clearly have strong command of the subject.",
    "Very impressive — you demonstrated both depth and clarity throughout.",
]

_OPENING_GOOD = [
    "Solid interview overall.",
    "Good effort — you showed a strong foundation in the key areas.",
    "Well done — most answers hit the mark.",
]

_OPENING_FAIR = [
    "Decent attempt, though there is clear room for improvement.",
    "You showed potential but the answers need more depth.",
    "A reasonable start — a few targeted improvements will go a long way.",
]

_OPENING_POOR = [
    "There is significant room to grow here.",
    "The answers need more structure and technical grounding.",
    "Let's work on building stronger, more focused responses.",
]

_CLOSINGS = [
    "Keep practising — every mock interview brings you closer to your goal.",
    "With focused preparation you will see rapid improvement.",
    "Review the feedback above, work on one area at a time, and keep going.",
    "Strong candidates iterate quickly — use this feedback and try again.",
]

# Strength / improvement phrases keyed by dimension
_STRENGTH_PHRASES = {
    "technical":     [
        "You showed solid technical knowledge.",
        "Your technical answers demonstrated good understanding.",
        "You handled technical questions with confidence.",
    ],
    "communication": [
        "Your answers were clearly structured and easy to follow.",
        "You communicated your ideas effectively.",
        "Your explanations were coherent and well-organised.",
    ],
    "confidence": [
        "You came across as composed and self-assured.",
        "Your delivery was confident and professional.",
        "Your calm demeanour made a strong positive impression.",
    ],
}

_IMPROVEMENT_PHRASES = {
    "technical": [
        "Focus on adding more technical depth — specifics and metrics matter.",
        "Try to back your answers with concrete technical examples.",
        "Dig deeper into the 'how' and 'why' behind your technical choices.",
    ],
    "communication": [
        "Work on structuring answers using the STAR method (Situation, Task, Action, Result).",
        "Be more concise — aim for clear, direct sentences.",
        "Reduce filler words and get to the point faster.",
    ],
    "confidence": [
        "Maintain more consistent eye contact with the camera.",
        "Work on your posture — sitting upright signals confidence.",
        "Project a calmer, more assured presence during your answers.",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _opening(overall: int) -> str:
    if overall >= 80:
        return random.choice(_OPENING_EXCELLENT)
    if overall >= 65:
        return random.choice(_OPENING_GOOD)
    if overall >= 45:
        return random.choice(_OPENING_FAIR)
    return random.choice(_OPENING_POOR)


def _best_and_worst(scores: Dict[str, int]) -> tuple[str, str]:
    """Return (best_dimension, worst_dimension) excluding overall_score."""
    dims = {k: v for k, v in scores.items() if k != "overall_score"}
    best  = max(dims, key=dims.get)
    worst = min(dims, key=dims.get)
    return best, worst


_DIM_NAMES = {
    "technical_score":     "technical",
    "communication_score": "communication",
    "confidence_score":    "confidence",
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------


def generate_feedback(
    scores:         Dict[str, int],
    round_analyses: List[Dict[str, object]],
) -> str:
    """
    Compose a paragraph of human-like feedback.

    Parameters
    ----------
    scores         : output of scoring_engine.compute_scores()
    round_analyses : list of nlp_analyzer.analyze_round() dicts
    """
    overall = scores.get("overall_score", 50)
    parts   = [_opening(overall)]

    # ── Best dimension strength ──────────────────────────────────────────
    best_key, worst_key = _best_and_worst(scores)
    best_dim  = _DIM_NAMES.get(best_key,  "technical")
    worst_dim = _DIM_NAMES.get(worst_key, "communication")

    best_score  = scores[best_key]
    worst_score = scores[worst_key]

    if best_score >= 60:
        parts.append(random.choice(_STRENGTH_PHRASES[best_dim]))

    # ── Specific round observations ──────────────────────────────────────
    round_notes: List[str] = []
    for ra in round_analyses:
        relevance     = int(ra.get("relevance",    50))
        completeness  = int(ra.get("completeness", 50))
        clarity       = int(ra.get("clarity",      50))

        if relevance < 40:
            round_notes.append("Some answers drifted off-topic — keep your responses focused on the question asked.")
            break
        if completeness < 35:
            round_notes.append("Several answers were too brief — back your points with specific examples and numbers.")
            break
        if clarity < 35:
            round_notes.append("Work on sentence structure — shorter, crisper sentences improve comprehension significantly.")
            break

    if round_notes:
        parts.extend(round_notes)

    # ── Primary improvement area ─────────────────────────────────────────
    if worst_score < 75:
        parts.append(random.choice(_IMPROVEMENT_PHRASES[worst_dim]))

    # ── Closing ──────────────────────────────────────────────────────────
    parts.append(random.choice(_CLOSINGS))

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Per-round micro-feedback
# ---------------------------------------------------------------------------


def generate_round_feedback(
    relevance:    int,
    completeness: int,
    clarity:      int,
) -> str:
    """Short one-liner feedback for a single Q&A round."""
    avg = (relevance + completeness + clarity) // 3
    if avg >= 75:
        return "Strong answer — relevant, well-structured, and clear."
    if relevance < 40:
        return "Answer didn't fully address the question — try to stay on-topic."
    if completeness < 40:
        return "Answer was too brief — elaborate with examples and specifics."
    if clarity < 40:
        return "Consider simplifying your sentences for clearer delivery."
    return "Decent answer — more depth and concrete examples would improve it."
