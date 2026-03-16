from __future__ import annotations
from typing import List

def generate_question(role: str, history: List[str]) -> str:
    """Return a generated question based on role and history.

    This is a temporary mock implementation. It returns deterministic
    questions from a small pool. A real implementation could call an LLM.
    """
    base_questions = [
        "Tell me about yourself.",
        "Why are you interested in this role?",
        "Describe a challenge you faced and how you resolved it.",
        "How do you prioritize tasks when working under pressure?",
        "Where do you see yourself in five years?",
        "Tell me about a time you received critical feedback.",
        "How would you handle a disagreement with a coworker?",
        "Describe a project you are proud of.",
    ]

    idx = len(history) % len(base_questions)
    return base_questions[idx]
"""Simple question generator for interview sessions.

This module currently provides a static list of questions and a simple
iterator-style generator. It's intentionally simple (no LLM) so it is
deterministic and suitable for testing and offline usage.
"""

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


class QuestionGenerator:
    def __init__(self, role: Optional[str] = None, questions: Optional[List[str]] = None) -> None:
        """Create a QuestionGenerator.

        Backwards-compatible: callers may still pass a list via `questions`.
        If `questions` is provided it takes precedence. Otherwise, if `role`
        is provided and matches an entry in `ROLE_QUESTIONS` we use that set
        and log the selection. If neither is provided we fall back to
        `DEFAULT_QUESTIONS`.
        """
        if questions:
            self._questions = list(questions)
        elif role:
            qs = ROLE_QUESTIONS.get(role.lower())
            if qs is None:
                log.info("Role '%s' not recognized, falling back to default questions", role)
                self._questions = list(DEFAULT_QUESTIONS)
            else:
                log.info("Role selected: %s", role)
                self._questions = list(qs)
        else:
            self._questions = list(DEFAULT_QUESTIONS)
        self._index = 0

    def next_question(self) -> Optional[str]:
        """Return the next question or None when exhausted."""
        if self._index >= len(self._questions):
            return None
        q = self._questions[self._index]
        self._index += 1
        log.debug("QuestionGenerator.next_question -> %s", q)
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
