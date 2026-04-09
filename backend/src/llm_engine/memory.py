"""
memory.py
---------
Conversation history management for the V5 AI Interviewer.

Handles windowed context building — only the last N rounds are sent
to the LLM to keep token usage bounded while maintaining coherence.

Also tracks follow-up chain depth so the engine knows when to stop
probing and move to a new topic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class RoundMemory:
    """One round of conversation context."""
    question:       str
    answer:         str
    score:          Optional[int]  = None
    feedback:       Optional[str]  = None
    expected_answer: Optional[str] = None
    gap_analysis:    Optional[str] = None
    improvement:     Optional[str] = None
    is_follow_up:   bool           = False
    follow_up_depth: int            = 0


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------


def build_context(
    rounds:  List[RoundMemory],
    window:  int = 3,
) -> str:
    """
    Format the last ``window`` rounds into a string for the LLM prompt.

    Skipped rounds are included with a "[SKIPPED]" marker so the LLM
    understands the candidate chose not to answer.

    Parameters
    ----------
    rounds : full list of rounds so far
    window : how many recent rounds to include (default 3)

    Returns
    -------
    str — formatted conversation context, or empty string if no rounds
    """
    if not rounds:
        return ""

    # Take the last `window` rounds
    recent = rounds[-window:]

    lines: list[str] = []
    for i, r in enumerate(recent):
        idx = len(rounds) - len(recent) + i + 1
        q_label = f"Q{idx}"
        if r.is_follow_up:
            q_label += " (follow-up)"

        answer_text = r.answer if r.answer and r.answer.upper() != "SKIPPED" else "[SKIPPED]"

        lines.append(f"{q_label}: {r.question}")
        lines.append(f"A{idx}: {answer_text}")

        if r.score is not None:
            lines.append(f"Score: {r.score}/10")
        if r.feedback:
            lines.append(f"Feedback: {r.feedback}")

        lines.append("")  # blank line between rounds

    return "\n".join(lines).strip()


def get_follow_up_depth(rounds: List[RoundMemory]) -> int:
    """
    Count how many consecutive follow-up questions are at the tail
    of the conversation (the current follow-up chain depth).

    Returns 0 if the last question was a new topic.
    """
    depth = 0
    for r in reversed(rounds):
        if r.is_follow_up:
            depth += 1
        else:
            break
    return depth


def build_transcript(rounds: List[RoundMemory]) -> str:
    """
    Build a full transcript string for the final summary prompt.
    Includes all rounds (not windowed).
    """
    lines: list[str] = []
    for i, r in enumerate(rounds):
        prefix = f"Q{i+1}"
        if r.is_follow_up:
            prefix += " (follow-up)"

        answer = r.answer if r.answer and r.answer.upper() != "SKIPPED" else "[SKIPPED]"
        lines.append(f"{prefix}: {r.question}")
        lines.append(f"A{i+1}: {answer}")
        lines.append("")

    return "\n".join(lines).strip()


def build_scores_summary(rounds: List[RoundMemory]) -> str:
    """
    Build a compact scores summary for the final prompt.
    """
    parts: list[str] = []
    for i, r in enumerate(rounds):
        label = "follow-up" if r.is_follow_up else "new topic"
        score = r.score if r.score is not None else "N/A"
        skipped = " [SKIPPED]" if (r.answer or "").upper() == "SKIPPED" else ""
        parts.append(f"Round {i+1} ({label}): {score}/10{skipped}")
    return "\n".join(parts)
