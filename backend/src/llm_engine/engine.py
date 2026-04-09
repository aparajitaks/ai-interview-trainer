"""
engine.py
---------
Core V5 AI Interviewer engine.

Central function: ``generate_next_step()``

Combines answer evaluation, cross-questioning decision, and next question
generation into a **single LLM call**.  Falls back to heuristic logic
when the Gemini API is unavailable.

Cross-questioning logic
~~~~~~~~~~~~~~~~~~~~~~~
  score < 6  AND  follow_up_count < 2  →  ask a probing follow-up
  score >= 6  OR  follow_up_count >= 2  →  move to a new topic
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from src.llm_engine.client  import call_llm, call_llm_json, is_ready
from src.llm_engine.memory  import RoundMemory, build_context, get_follow_up_depth
from src.llm_engine.prompts import (
    build_next_step_prompt,
    build_opening_prompt,
    build_final_summary_prompt,
)

logger = logging.getLogger(__name__)

# Follow-up threshold — scores below this trigger a probing follow-up
FOLLOW_UP_THRESHOLD = 6
MAX_FOLLOW_UPS      = 2


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class NextStepResult:
    """Output of generate_next_step()."""
    score:            int
    feedback:         str
    expected_answer:  str
    gap_analysis:     str
    improvement:      str
    next_question:    str
    follow_up:        bool
    follow_up_reason: Optional[str] = None

    @property
    def is_follow_up(self) -> bool:
        """Backward-compatible alias used by existing routes/UI."""
        return self.follow_up


# ---------------------------------------------------------------------------
# Heuristic question banks (fallback when LLM is unavailable)
# ---------------------------------------------------------------------------

_BANKS: dict[str, List[str]] = {
    "ai_ml": [
        "Tell me about your background in AI/ML and what drew you to this field.",
        "Explain the bias–variance tradeoff and how you manage it in practice.",
        "Walk me through how you would design a recommendation engine from scratch.",
        "How do you evaluate a model beyond accuracy? Which metrics matter most?",
        "Describe a time you deployed an ML model to production. What challenges came up?",
        "How do you handle data drift in a production ML system?",
        "Explain the difference between fine-tuning and training from scratch.",
        "What's your approach to feature engineering for tabular data?",
    ],
    "software": [
        "Tell me about your engineering background and a project you're most proud of.",
        "How do you design a system for high availability? Walk me through your approach.",
        "What's your philosophy on writing testable, maintainable code?",
        "Describe how you optimised a slow query or bottleneck in a production system.",
        "How do you stay current with new technologies? Give a recent example.",
        "Explain how you'd design a rate limiter for an API.",
        "What's your experience with CI/CD pipelines and deployment strategies?",
        "How do you approach debugging a production incident under time pressure?",
    ],
    "data": [
        "Walk me through your data engineering background and the scale of data you've worked with.",
        "How would you design a real-time data pipeline? What tools would you use?",
        "Describe how you ensure data quality and consistency in a large-scale system.",
        "What's your experience with data warehousing and OLAP vs OLTP trade-offs?",
        "How do you collaborate with data scientists and analysts on shared infrastructure?",
        "Explain how you'd handle schema evolution in a streaming pipeline.",
        "What's your approach to data partitioning and indexing at scale?",
        "How do you monitor and alert on data pipeline health?",
    ],
    "default": [
        "Tell me about yourself and what excites you most about this opportunity.",
        "Describe a challenging problem you solved recently. Walk me through your approach.",
        "Tell me about a time you had to learn something complex very quickly.",
        "Describe a situation where you disagreed with a colleague. How did you handle it?",
        "Where do you see yourself in 2–3 years, and how does this role fit that vision?",
        "How do you prioritise competing tasks when everything feels urgent?",
        "Tell me about a project that failed. What did you learn?",
        "How do you give and receive constructive feedback?",
    ],
}

_FOLLOW_UP_TEMPLATES = [
    "Can you elaborate on that? Specifically, what was your approach to {topic}?",
    "You mentioned {topic} — can you walk me through a concrete example?",
    "That's an interesting point. How would you handle the edge case where {topic} fails?",
    "Let's dig deeper — what trade-offs did you consider regarding {topic}?",
    "Can you be more specific about the technical details of {topic}?",
]

_DEFAULT_EXPECTED = "A strong answer should be structured, role-relevant, and backed by one concrete example with measurable impact."
_DEFAULT_GAP = "The answer needs clearer structure and more specific technical evidence."
_DEFAULT_IMPROVEMENT = "Use STAR: briefly state context, action, and measurable result in 3-4 concise sentences."


def _pick_bank(domain: str) -> List[str]:
    dl = domain.lower()
    if any(k in dl for k in ["ai", "ml", "machine learning", "deep learning", "nlp", "data scientist"]):
        return _BANKS["ai_ml"]
    if any(k in dl for k in ["data engineer", "data platform", "etl", "pipeline"]):
        return _BANKS["data"]
    if any(k in dl for k in ["software", "backend", "frontend", "fullstack", "sde", "developer", "devops"]):
        return _BANKS["software"]
    return _BANKS["default"]


# ---------------------------------------------------------------------------
# Opening question
# ---------------------------------------------------------------------------


def generate_opening(domain: str) -> str:
    """Generate the first interview question for the given domain."""
    if is_ready():
        try:
            prompt = build_opening_prompt(domain)
            return call_llm(prompt)
        except Exception as exc:
            logger.warning("LLM opening failed (%s) — using bank.", exc)

    return _pick_bank(domain)[0]


# ---------------------------------------------------------------------------
# Core function: evaluate + decide + generate in one call
# ---------------------------------------------------------------------------


def generate_next_step(
    question:        str,
    answer:          str,
    domain:          str,
    history:         Optional[List[RoundMemory]] = None,
    follow_up_count: int = 0,
) -> NextStepResult:
    """
    Evaluate the candidate's answer, decide whether to cross-question or
    move on, and generate the next question — all in a single LLM call.

    Parameters
    ----------
    question        : the question that was just asked
    answer          : the candidate's answer
    domain          : job role / domain
    history         : full conversation history as RoundMemory objects
    follow_up_count : current depth in the follow-up chain (0 = new topic)

    Returns
    -------
    NextStepResult with score, feedback, next_question, is_follow_up
    """
    # Try LLM path first
    if is_ready():
        try:
            return _llm_next_step(question, answer, domain, history or [], follow_up_count)
        except Exception as exc:
            logger.warning("LLM next-step failed (%s) — heuristic fallback.", exc)

    # Heuristic fallback
    return _heuristic_next_step(question, answer, domain, history or [], follow_up_count)


def _llm_next_step(
    question:        str,
    answer:          str,
    domain:          str,
    history:         List[RoundMemory],
    follow_up_count: int,
) -> NextStepResult:
    """LLM-powered next step via structured JSON prompt."""
    context = build_context(history, window=3)

    prompt = build_next_step_prompt(
        domain          = domain,
        question        = question,
        answer          = answer,
        history         = context,
        follow_up_count = follow_up_count,
    )

    data = call_llm_json(prompt)

    score        = max(0, min(10, int(data.get("score", 5))))
    feedback     = str(data.get("feedback", "No feedback available."))
    expected     = str(data.get("expected_answer", _DEFAULT_EXPECTED))
    gap          = str(data.get("gap_analysis", _DEFAULT_GAP))
    improvement  = str(data.get("improvement", _DEFAULT_IMPROVEMENT))
    needs_follow = bool(data.get("follow_up", data.get("needs_follow_up", False)))
    follow_reason = data.get("follow_up_reason")
    next_q       = str(data.get("next_question", "Tell me more about your experience."))

    # Enforce follow-up cap at the engine level (safety net)
    if needs_follow and follow_up_count >= MAX_FOLLOW_UPS:
        needs_follow  = False
        follow_reason = None
        logger.info("Capping follow-ups at %d — moving to new topic.", MAX_FOLLOW_UPS)

    logger.info(
        "LLM next-step — score=%d  follow_up=%s  depth=%d",
        score, needs_follow, follow_up_count,
    )

    return NextStepResult(
        score            = score,
        feedback         = feedback,
        expected_answer  = expected,
        gap_analysis     = gap,
        improvement      = improvement,
        next_question    = next_q,
        follow_up        = needs_follow,
        follow_up_reason = follow_reason if needs_follow else None,
    )


def _heuristic_next_step(
    question:        str,
    answer:          str,
    domain:          str,
    history:         List[RoundMemory],
    follow_up_count: int,
) -> NextStepResult:
    """Heuristic fallback — no LLM needed."""
    import re

    # Word-count based scoring (curve: ~8 words per point)
    # 0 words → 0,  16 words → 2,  40 words → 5,  48 words → 6,  80 words → 10
    wc    = len(answer.split()) if answer and answer.upper() != "SKIPPED" else 0
    score = min(10, max(1, wc // 8)) if wc > 0 else 0

    # Generate feedback
    if score == 0:
        feedback = "No answer provided."
    elif score < 4:
        feedback = "Good attempt, but the answer is too brief and misses key details."
    elif score < 6:
        feedback = "You covered the basics, but the explanation needs more depth and examples."
    elif score < 8:
        feedback = "Clear answer with good structure. Add stronger technical proof and metrics."
    else:
        feedback = "Strong answer: clear, relevant, and backed by concrete detail."

    expected_answer = (
        "An ideal answer should define the core concept, explain trade-offs, and include one practical example with outcome."
    )
    if score >= 8:
        gap_analysis = "Minor gap: add one more metric or edge case to make the answer interview-ready."
        improvement = "Keep this structure and add one quantified impact point (for example, latency reduced by X%)."
    elif score >= 6:
        gap_analysis = "Main gap: the answer is correct but light on technical depth and measurable impact."
        improvement = "Add one concrete project example and one metric to prove impact."
    elif score >= 4:
        gap_analysis = "Main gap: the answer is generic and does not clearly explain your decisions."
        improvement = "Use STAR in 3-4 lines and explain why you chose that approach."
    else:
        gap_analysis = "Main gap: the answer does not provide enough relevant content to assess capability."
        improvement = "Start with a simple definition, then give one concrete example and result."

    # Cross-questioning decision
    needs_follow = score < FOLLOW_UP_THRESHOLD and follow_up_count < MAX_FOLLOW_UPS and score > 0
    follow_reason = None

    if needs_follow:
        # Extract a topic keyword from the question for the follow-up
        words = re.findall(r'\b[a-z]{4,}\b', question.lower())
        topic = words[-1] if words else "that concept"
        import random
        template = random.choice(_FOLLOW_UP_TEMPLATES)
        next_q = template.format(topic=topic)
        follow_reason = f"Answer scored {score}/10 — probing deeper."
    else:
        # Pick next question from bank
        bank = _pick_bank(domain)
        answered_count = len(history) + 1
        next_q = bank[answered_count % len(bank)]

    return NextStepResult(
        score            = score,
        feedback         = feedback,
        expected_answer  = expected_answer,
        gap_analysis     = gap_analysis,
        improvement      = improvement,
        next_question    = next_q,
        follow_up        = needs_follow,
        follow_up_reason = follow_reason,
    )


# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------


def generate_final_summary(
    domain:  str,
    history: List[RoundMemory],
) -> dict:
    """
    Generate a holistic final evaluation from the full conversation history.

    Returns a dict compatible with the existing final feedback schema.
    """
    from src.llm_engine.memory import build_transcript, build_scores_summary

    if is_ready() and history:
        try:
            transcript = build_transcript(history)
            scores_str = build_scores_summary(history)
            prompt     = build_final_summary_prompt(domain, transcript, scores_str)
            return json.loads(call_llm(prompt, json_mode=True))
        except Exception as exc:
            logger.warning("LLM final summary failed (%s) — heuristic.", exc)

    # Heuristic fallback
    return _heuristic_final_summary(domain, history)


def _heuristic_final_summary(domain: str, history: List[RoundMemory]) -> dict:
    """Heuristic final summary — no LLM needed."""
    real_scores   = [r.score for r in history if r.score and r.score > 0]
    skipped_count = sum(1 for r in history if not r.answer or (r.answer or "").upper() == "SKIPPED")
    total         = len(history)

    if not real_scores:
        return {
            "summary":             f"No questions were answered in the {domain} interview.",
            "strengths":           [],
            "improvements":        ["Answer at least a few questions for a meaningful evaluation."],
            "overall_score":       0,
            "communication_score": 0,
            "technical_score":     0,
            "confidence_score":    0,
        }

    avg = sum(real_scores) / len(real_scores)
    answer_rate = len(real_scores) / total if total > 0 else 1.0
    norm = int(avg * 10 * answer_rate)

    follow_up_count = sum(1 for r in history if r.is_follow_up)

    return {
        "summary": (
            f"Completed {len(real_scores)}/{total} rounds for {domain}. "
            f"Average score: {avg:.1f}/10. "
            f"{follow_up_count} follow-up question(s) were asked."
            + (f" {skipped_count} skipped." if skipped_count else "")
        ),
        "strengths": [
            "Engaged with the interview process",
            "Demonstrated willingness to tackle challenging questions",
        ],
        "improvements": [
            "Use the STAR method to structure answers",
            "Include quantitative metrics and concrete examples",
        ] + (["Try to answer all questions — skipping lowers your score"] if skipped_count else []),
        "overall_score":       norm,
        "communication_score": max(0, norm - 5),
        "technical_score":     max(0, norm + 5),
        "confidence_score":    max(0, norm),
    }
