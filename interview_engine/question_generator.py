from __future__ import annotations

from typing import List, Optional
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

try:
    from nlp_models.llm_generator import generate_question as llm_generate
except Exception:
    llm_generate = None

try:
    from interview_engine.keyword_detector import detect_keywords, strength_from_answer
except Exception:
    detect_keywords = None
    strength_from_answer = None


DEFAULT_QUESTIONS: List[str] = [
    "Tell me about yourself.",
    "Why do you want this role?",
    "Describe a challenging problem you solved.",
    "How do you handle tight deadlines?",
    "Do you work better alone or in a team?",
]


ROLE_QUESTIONS = {
    "frontend": [
        "Describe your experience building responsive UIs.",
        "How do you optimize web performance?",
        "Explain CSS specificity and how you manage styles at scale.",
        "How do you approach accessibility (a11y) in your projects?",
        "Which frontend frameworks have you used and why?",
    ],
    "backend": [
        "Describe a scalable backend system you've designed.",
        "How do you ensure data consistency in distributed systems?",
        "Explain how you approach API versioning and migration.",
        "What strategies do you use for caching and performance?",
        "How do you secure services and manage secrets?",
    ],
    "ml": [
        "Describe a machine learning project you led end-to-end.",
        "How do you evaluate model performance and avoid overfitting?",
        "Explain how you would deploy a model to production.",
        "What data preprocessing steps do you commonly use?",
        "How do you monitor model drift and maintain models in prod?",
    ],
        "data": [
            "Describe your experience with data pipelines and ETL.",
            "How do you handle missing or corrupt data in production?",
            "Explain a time you designed features for a predictive model.",
            "Which statistical tests do you use to validate assumptions?",
            "How do you monitor data quality and correctness in pipelines?",
        ],
}


def generate_question(role: str, history: List[str], last_answer: Optional[str] = None, difficulty: Optional[str] = None, keywords: Optional[List[str]] = None) -> str:
    """Generate the next question. Prefer LLM-backed generator when available.

    Parameters
    - role: role name (e.g., 'ml')
    - history: list of previous question texts
    - last_answer: optional text of the candidate's last answer
    """
    # If we have an LLM generator available, attempt a focused generation.
    try:
        # prefer caller-provided keywords/difficulty; otherwise try to compute
        if keywords is None and detect_keywords and last_answer:
            try:
                keywords = detect_keywords(role or "", last_answer)
            except Exception:
                keywords = []
        if difficulty is None and strength_from_answer and last_answer:
            try:
                s = strength_from_answer(last_answer, keywords or [])
                if s == "weak":
                    difficulty = "easy"
                elif s == "strong":
                    difficulty = "hard"
                else:
                    difficulty = "medium"
            except Exception:
                difficulty = None

        if llm_generate:
            q = llm_generate(role or "", history or [], last_answer, difficulty, keywords)
            if q:
                return q
    except Exception:
        log.exception("LLM generation failed; falling back to deterministic generator")

    # Fallback to deterministic behavior
    pool = DEFAULT_QUESTIONS
    if role and role.lower() in ROLE_QUESTIONS:
        pool = ROLE_QUESTIONS[role.lower()]
    # Deterministic adaptive rules for fallback generator
    if not history:
        # first question for the role
        return pool[0] if pool else DEFAULT_QUESTIONS[0]

    # if keywords present, ask a focused deeper question
    if keywords:
        top = keywords[0]
        return f"Can you explain {top} in more detail and how you applied it?"

    # difficulty influences which element to pick: easy -> early questions, hard -> deeper questions
    if difficulty == "easy":
        return pool[0]
    if difficulty == "hard":
        return pool[-1]

    # medium or unknown - rotate through pool
    idx = len(history) % len(pool) if pool else 0
    return pool[idx]


class QuestionGenerator:
    def __init__(self, role: Optional[str] = None, questions: Optional[List[str]] = None) -> None:
        if questions:
            self._questions = list(questions)
        elif role:
            self._questions = list(ROLE_QUESTIONS.get(role.lower(), DEFAULT_QUESTIONS))
        else:
            self._questions = list(DEFAULT_QUESTIONS)
        self._index = 0

    def next_question(self) -> Optional[str]:
        if self._index >= len(self._questions):
            return None
        q = self._questions[self._index]
        self._index += 1
        return q

    def reset(self) -> None:
        self._index = 0

    def all_questions(self) -> List[str]:
        return list(self._questions)


def test_generator() -> None:
    gen = QuestionGenerator()
    q = gen.next_question()
    while q:
        log.info("Next question: %s", q)
        q = gen.next_question()


if __name__ == "__main__":
    test_generator()
