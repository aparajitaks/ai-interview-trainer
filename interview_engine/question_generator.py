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


class QuestionGenerator:
    def __init__(self, questions: Optional[List[str]] = None) -> None:
        self._questions = list(questions or DEFAULT_QUESTIONS)
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
