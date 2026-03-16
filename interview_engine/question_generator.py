from __future__ import annotations

from typing import List, Optional
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


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
}


def generate_question(role: str, history: List[str]) -> str:
    # simple deterministic generator - choose next from DEFAULT_QUESTIONS based on history length
    pool = DEFAULT_QUESTIONS
    if role and role.lower() in ROLE_QUESTIONS:
        pool = ROLE_QUESTIONS[role.lower()]
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
