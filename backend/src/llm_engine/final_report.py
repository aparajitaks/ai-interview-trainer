"""
final_report.py
---------------
Deep coaching report generation for completed interviews.

This module is intentionally used only at end-of-interview so the live
interview loop remains fast and non-interruptive.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from src.interview.session import Round
from src.llm_engine.client import call_llm_json, is_ready

logger = logging.getLogger(__name__)


def _is_skipped(answer: str | None) -> bool:
    if answer is None:
        return True
    val = answer.strip()
    return val == "" or val.upper() == "SKIPPED"


def _build_prompt(question: str, user_answer: str) -> str:
    return (
        "You are an expert interview coach.\n\n"
        "For the following interview question:\n\n"
        f"Question: {question}\n"
        f"User Answer: {user_answer}\n\n"
        "If the user_answer is empty, null, or 'SKIPPED':\n"
        "* Assume the candidate does not know the concept\n"
        "* Teach from scratch clearly and simply\n\n"
        "Return STRICT JSON:\n"
        "{\n"
        '"score": number (0–10),\n'
        '"feedback": "short evaluation",\n'
        '"expected_answer": "ideal interview answer",\n'
        '"explanation": "simple concept explanation",\n'
        '"how_to_answer": "structured approach (definition + example + impact)",\n'
        '"key_points": ["point1", "point2", "point3"],\n'
        '"example": "real-world example"\n'
        "}\n\n"
        "IMPORTANT:\n"
        "* Keep explanations concise\n"
        "* Make it beginner-friendly\n"
        "* Avoid long paragraphs\n"
        "* Be practical and interview-focused"
    )


def _heuristic_review(question: str, user_answer: str) -> Dict[str, Any]:
    skipped = _is_skipped(user_answer)
    if skipped:
        return {
            "score": 0,
            "feedback": "You skipped this question.",
            "expected_answer": "Start by defining the concept, then give a practical example and measurable impact.",
            "explanation": "This topic is foundational for interviews. Interviewers expect a basic definition and real usage.",
            "how_to_answer": "Use definition + one project example + impact in 3-4 concise sentences.",
            "key_points": ["Define the core concept", "Show where you used it", "State the outcome with a metric"],
            "example": "In my last project, I implemented this approach and reduced API latency by 35%.",
        }

    wc = len(user_answer.split())
    score = max(3, min(9, wc // 12 + 3))
    return {
        "score": score,
        "feedback": "Decent attempt. Add clearer structure and one concrete metric.",
        "expected_answer": "A strong answer defines the concept, explains trade-offs, and gives one practical example with measurable impact.",
        "explanation": "Interviewers look for both understanding and execution. Keep it clear, specific, and outcome-oriented.",
        "how_to_answer": "Start with definition, then example, then impact metric.",
        "key_points": ["Clear definition", "Real project context", "Quantified result"],
        "example": "I used this in production to improve throughput by 20% while reducing failures.",
    }


def generate_question_review(question: str, user_answer: str) -> Dict[str, Any]:
    if is_ready():
        try:
            data = call_llm_json(_build_prompt(question, user_answer))
            key_points = data.get("key_points", [])
            if not isinstance(key_points, list):
                key_points = []
            return {
                "score": max(0, min(10, int(data.get("score", 0)))),
                "feedback": str(data.get("feedback", "")),
                "expected_answer": str(data.get("expected_answer", "")),
                "explanation": str(data.get("explanation", "")),
                "how_to_answer": str(data.get("how_to_answer", "")),
                "key_points": [str(x) for x in key_points[:5]],
                "example": str(data.get("example", "")),
            }
        except Exception as exc:
            logger.warning("Final report question review failed; using heuristic. err=%s", exc)

    return _heuristic_review(question, user_answer)


def build_final_report(rounds: List[Round]) -> Dict[str, Any]:
    reviews: List[Dict[str, Any]] = []
    for r in rounds:
        if r.answer is None:
            continue

        user_answer = r.answer
        review = generate_question_review(r.question, user_answer)

        # Persist back to round for session/debug retrieval
        r.score = review["score"]
        r.feedback = review["feedback"]
        r.expected_answer = review["expected_answer"]
        r.explanation = review["explanation"]
        r.how_to_answer = review["how_to_answer"]
        r.key_points = review["key_points"]
        r.example = review["example"]

        reviews.append({
            "question": r.question,
            "user_answer": user_answer,
            "score": review["score"],
            "feedback": review["feedback"],
            "expected_answer": review["expected_answer"],
            "explanation": review["explanation"],
            "how_to_answer": review["how_to_answer"],
            "key_points": review["key_points"],
            "example": review["example"],
        })

    if not reviews:
        return {
            "final_score": 0,
            "summary": "No submitted answers were found in this interview session.",
            "weak_areas": [],
            "improvement_plan": {
                "topics_to_study": [],
                "suggested_practice": [
                    "Complete at least one full mock interview session.",
                    "Answer every question, even with a short attempt.",
                ],
                "learning_path": [
                    "Step 1: Start with core interview fundamentals.",
                    "Step 2: Practice 5 role-specific questions.",
                    "Step 3: Review feedback and repeat weekly.",
                ],
            },
            "question_reviews": [],
        }

    avg = round(sum(int(r["score"]) for r in reviews) / len(reviews), 1)
    weak_areas = _detect_weak_areas(reviews)
    improvement_plan = _build_improvement_plan(weak_areas, avg)
    summary = (
        f"You completed {len(reviews)} question(s). "
        f"Average score: {avg}/10. "
        "Review each question to learn the expected structure and improve your next interview."
    )
    return {
        "final_score": avg,
        "summary": summary,
        "weak_areas": weak_areas,
        "improvement_plan": improvement_plan,
        "question_reviews": reviews,
    }


def _detect_weak_areas(reviews: List[Dict[str, Any]], threshold: int = 5) -> List[str]:
    """
    Detect weak topics from low-scoring questions.

    - Tracks questions with score <= threshold
    - Extracts a compact topic label from each question
    - Returns deduplicated weak area list
    """
    weak_topics: List[str] = []
    for item in reviews:
        score = int(item.get("score", 0))
        if score > threshold:
            continue
        question = str(item.get("question", ""))
        topic = _extract_topic(question)
        if topic not in weak_topics:
            weak_topics.append(topic)
    return weak_topics


def _extract_topic(question: str) -> str:
    q = question.strip()
    ql = q.lower()

    # High-value interview themes first
    topic_map = {
        "system design": ["system design", "design a system", "scalable", "high availability"],
        "machine learning fundamentals": ["bias", "variance", "model", "feature engineering", "training"],
        "model evaluation": ["metric", "accuracy", "precision", "recall", "f1", "evaluate"],
        "data pipelines": ["pipeline", "etl", "streaming", "batch", "schema evolution"],
        "api design": ["api", "endpoint", "rate limiter", "rest", "http"],
        "databases": ["sql", "query", "index", "oltp", "olap", "database"],
        "testing": ["test", "unit test", "integration", "qa"],
        "debugging": ["debug", "incident", "bottleneck", "root cause"],
        "communication": ["disagreed", "conflict", "feedback", "collaborate"],
        "behavioral": ["tell me about", "time you", "challenge", "yourself"],
    }
    for label, keys in topic_map.items():
        if any(k in ql for k in keys):
            return label

    # Fallback: derive from longest meaningful tokens
    tokens = re.findall(r"[a-zA-Z]{4,}", ql)
    stop = {
        "what", "when", "where", "which", "with", "from", "this", "that",
        "would", "about", "your", "have", "into", "through", "describe",
        "explain", "walk", "tell", "role", "interview", "candidate", "answer",
    }
    meaningful = [t for t in tokens if t not in stop]
    if not meaningful:
        return "general interview fundamentals"
    return " ".join(meaningful[:2])


def _build_improvement_plan(weak_areas: List[str], final_score: float) -> Dict[str, List[str]]:
    topics = weak_areas[:6] if weak_areas else ["general interview fundamentals"]

    base_practice = [
        "Do one timed mock interview (30-40 minutes) every 2-3 days.",
        "Use the STAR format for each answer: Situation, Task, Action, Result.",
        "After each answer, add one measurable impact (%, time saved, revenue, latency, etc.).",
    ]

    if final_score < 4:
        extra_practice = [
            "Start with beginner explanations for each weak topic and restate them in your own words.",
            "Practice 3 short answers per day (60-90 seconds each) on core concepts.",
        ]
        path = [
            "Week 1: Build foundations for each weak topic (definitions + simple examples).",
            "Week 2: Practice structured answers with STAR on common interview questions.",
            "Week 3: Run 2 full mock interviews and review weak answers.",
        ]
    elif final_score < 7:
        extra_practice = [
            "For each weak area, prepare one project-based example and one trade-off discussion.",
            "Record answers and refine clarity, pacing, and conciseness.",
        ]
        path = [
            "Week 1: Strengthen weak topics with focused notes and examples.",
            "Week 2: Practice medium-to-hard interview questions with timed responses.",
            "Week 3: Simulate a full interview and improve top 3 weak answers.",
        ]
    else:
        extra_practice = [
            "Focus on advanced depth: edge cases, trade-offs, and system-level reasoning.",
            "Polish delivery: concise answers under 2 minutes with clear structure.",
        ]
        path = [
            "Week 1: Deepen advanced concepts in your weakest areas.",
            "Week 2: Practice senior-level scenario and design questions.",
            "Week 3: Run high-pressure mock interviews and optimize final delivery.",
        ]

    return {
        "topics_to_study": topics,
        "suggested_practice": base_practice + extra_practice,
        "learning_path": path,
    }
