"""
llm.py  (google-genai SDK)
--------------------------
LLM-powered question generation and answer evaluation using Google Gemini.

Production path  : Gemini 2.0 Flash via the new `google-genai` SDK.
                   Set GEMINI_API_KEY env var.
Development path : Rule-based question bank + heuristic scoring —
                   zero API keys required.
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (optional)
# ---------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_LLM_READY     = False
_client        = None

if GEMINI_API_KEY:
    try:
        from google import genai as _genai
        from google.genai import types as _gtypes
        _client    = _genai.Client(api_key=GEMINI_API_KEY)
        _LLM_READY = True
        logger.info("LLM: Gemini 2.0 Flash enabled (google-genai SDK).")
    except ImportError:
        logger.warning(
            "google-genai not installed — using rule-based fallback. "
            "Run: pip install google-genai"
        )
    except Exception as exc:
        logger.warning("Gemini init failed (%s) — rule-based fallback active.", exc)
else:
    logger.info(
        "GEMINI_API_KEY not set — using rule-based question bank. "
        "Set the env var to enable AI-generated questions."
    )

_MODEL = "models/gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Rule-based question banks (no API key needed)
# ---------------------------------------------------------------------------

_BANK: dict[str, List[str]] = {
    "ai_ml": [
        "Tell me about your background in AI/ML and what drew you to this field.",
        "Explain the bias–variance tradeoff and how you manage it in practice.",
        "Walk me through how you would design a recommendation engine from scratch.",
        "How do you evaluate a model beyond accuracy? Which metrics matter most?",
        "Describe a time you deployed an ML model to production. What challenges came up?",
    ],
    "software": [
        "Tell me about your engineering background and a project you're most proud of.",
        "How do you design a system for high availability? Walk me through your approach.",
        "What's your philosophy on writing testable, maintainable code?",
        "Describe how you optimised a slow query or bottleneck in a production system.",
        "How do you stay current with new technologies? Give a recent example.",
    ],
    "data": [
        "Walk me through your data engineering background and the scale of data you've worked with.",
        "How would you design a real-time data pipeline? What tools would you use?",
        "Describe how you ensure data quality and consistency in a large-scale system.",
        "What's your experience with data warehousing and OLAP vs OLTP trade-offs?",
        "How do you collaborate with data scientists and analysts on shared infrastructure?",
    ],
    "default": [
        "Tell me about yourself and what excites you most about this opportunity.",
        "Describe a challenging problem you solved recently. Walk me through your approach.",
        "Tell me about a time you had to learn something complex very quickly.",
        "Describe a situation where you disagreed with a colleague. How did you handle it?",
        "Where do you see yourself in 2–3 years, and how does this role fit that vision?",
    ],
}


def _pick_bank(role: str) -> List[str]:
    rl = role.lower()
    if any(k in rl for k in ["ai", "ml", "machine learning", "deep learning", "nlp"]):
        return _BANK["ai_ml"]
    if any(k in rl for k in ["data engineer", "data platform", "etl", "pipeline"]):
        return _BANK["data"]
    if any(k in rl for k in ["software", "backend", "frontend", "fullstack", "sde", "developer"]):
        return _BANK["software"]
    return _BANK["default"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_first_question(role: str) -> str:
    if _LLM_READY:
        try:
            return _gemini_question(role, [], [])
        except Exception as exc:
            logger.warning("Gemini question generation failed: %s", exc)
    return _pick_bank(role)[0]


def generate_next_question(
    role:      str,
    questions: List[str],
    answers:   List[str],
) -> str:
    if _LLM_READY:
        try:
            return _gemini_question(role, questions, answers)
        except Exception as exc:
            logger.warning("Gemini follow-up failed: %s", exc)
    bank = _pick_bank(role)
    return bank[len(questions) % len(bank)]


def evaluate_answer(question: str, answer: str, role: str) -> Tuple[str, int]:
    """Returns (feedback_text, score_1_to_10)."""
    if _LLM_READY:
        try:
            return _gemini_evaluate(question, answer, role)
        except Exception as exc:
            logger.warning("Gemini evaluation failed: %s", exc)
    return _heuristic_evaluate(answer, role)


def generate_final_feedback(
    role:      str,
    questions: List[str],
    answers:   List[str],
    scores:    List[int],
) -> dict:
    if _LLM_READY:
        try:
            return _gemini_final(role, questions, answers, scores)
        except Exception as exc:
            logger.warning("Gemini final feedback failed: %s", exc)
    return _heuristic_final(role, scores)


# ---------------------------------------------------------------------------
# Gemini implementations (google-genai SDK)
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are an expert technical interviewer at a top-tier technology company. "
    "Conduct focused, respectful, and progressively challenging interviews. "
    "Ask one question at a time. Be direct and concise."
)


def _gemini_question(role: str, questions: List[str], answers: List[str]) -> str:
    history = "".join(
        f"Q{i+1}: {q}\nA{i+1}: {a}\n\n"
        for i, (q, a) in enumerate(zip(questions, answers))
    )
    prompt = (
        f"{_SYSTEM}\n\n"
        f"Interviewing candidate for: {role}.\n"
        + (f"Interview so far:\n{history}\n" if history else "")
        + "Ask ONE focused technical question. Output only the question, no preamble."
    )
    resp = _client.models.generate_content(model=_MODEL, contents=prompt)
    return resp.text.strip()


def _gemini_evaluate(question: str, answer: str, role: str) -> Tuple[str, int]:
    prompt = (
        f"Role: {role}\n"
        f"Interview question: {question}\n"
        f"Candidate answer: {answer}\n\n"
        "Evaluate in 1–2 sentences covering technical depth and communication clarity. "
        "End with exactly: SCORE: N  (where N is 1–10)"
    )
    resp  = _client.models.generate_content(model=_MODEL, contents=prompt)
    raw   = resp.text.strip()
    score = 7
    lines = [l.strip() for l in raw.splitlines()]
    fb_lines: List[str] = []
    for line in lines:
        if line.upper().startswith("SCORE:"):
            try:
                score = max(1, min(10, int(line.split(":", 1)[1].strip().split()[0])))
            except (ValueError, IndexError):
                pass
        else:
            fb_lines.append(line)
    return " ".join(fb_lines).strip(), score


def _gemini_final(
    role: str, questions: List[str], answers: List[str], scores: List[int]
) -> dict:
    from google.genai import types as _gtypes
    transcript = "".join(
        f"Q{i+1}: {q}\nA{i+1}: {a}\n\n"
        for i, (q, a) in enumerate(zip(questions, answers))
    )
    prompt = (
        f"Evaluate this complete {role} interview transcript:\n\n{transcript}\n"
        "Return ONLY a valid JSON object with these exact keys:\n"
        '{"summary": "string", "strengths": ["string", "string"], '
        '"improvements": ["string", "string"], '
        '"overall_score": integer_0_to_100, '
        '"communication_score": integer_0_to_100, '
        '"technical_score": integer_0_to_100, '
        '"confidence_score": integer_0_to_100}'
    )
    resp = _client.models.generate_content(
        model    = _MODEL,
        contents = prompt,
        config   = _gtypes.GenerateContentConfig(
            response_mime_type="application/json"
        ),
    )
    return json.loads(resp.text)


# ---------------------------------------------------------------------------
# Heuristic fallbacks
# ---------------------------------------------------------------------------


def _heuristic_evaluate(answer: str, role: str) -> Tuple[str, int]:
    wc    = len(answer.split())
    score = min(10, max(4, wc // 12))
    tips  = {
        4:  "Add more detail and specific examples.",
        5:  "Good start — include quantitative results.",
        6:  "Solid. Structure answers with Situation–Action–Result.",
        7:  "Well structured. Add technical specifics.",
        8:  "Strong — great use of concrete examples.",
        9:  "Excellent depth and clarity.",
        10: "Outstanding — thorough and insightful.",
    }
    return tips.get(score, tips[7]) + f" (Role: {role}.)", score


def _heuristic_final(role: str, scores: List[int]) -> dict:
    # Separate real scores from skipped (0) scores
    real_scores   = [s for s in scores if s > 0]
    skipped_count = len(scores) - len(real_scores)
    total_count   = len(scores)

    # All skipped / empty → zero everything
    if not real_scores:
        return {
            "summary": (
                f"You skipped all {total_count} questions in the {role} interview. "
                "No evaluation is possible — try answering at least a few questions."
            ),
            "strengths": [],
            "improvements": [
                "Complete at least one round for a full evaluation",
                "Try answering even if you're unsure — partial answers are better than skips",
            ],
            "overall_score":       0,
            "communication_score": 0,
            "technical_score":     0,
            "confidence_score":    0,
        }

    # Calculate average from REAL answers only
    avg = sum(real_scores) / len(real_scores)

    # Apply skip penalty: scale down proportionally to answer rate
    answer_rate = len(real_scores) / total_count if total_count > 0 else 1.0
    penalized_avg = avg * answer_rate
    norm = int(penalized_avg * 10)

    return {
        "summary": (
            f"You completed {len(real_scores)} of {total_count} rounds "
            f"in the {role} interview. "
            f"Average score on answered questions: {avg:.1f}/10."
            + (f" ({skipped_count} question(s) were skipped.)" if skipped_count else "")
        ),
        "strengths": [
            "Participated in the interview",
            "Showed willingness to engage with challenging questions",
        ],
        "improvements": [
            "Use the STAR method (Situation, Task, Action, Result) to structure answers",
            "Quantify achievements with specific metrics where possible",
        ] + (["Try to answer all questions — skipping reduces your overall score"] if skipped_count else []),
        "overall_score":       norm,
        "communication_score": max(0, norm - 5),
        "technical_score":     max(0, norm + 5),
        "confidence_score":    max(0, norm),
    }
