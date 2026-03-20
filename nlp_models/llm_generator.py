"""Lightweight LLM-backed question generator.

This module tries to use the HuggingFace `transformers` pipeline for
text-generation when available (model chosen via environment variable
QGEN_MODEL). If transformers is not installed or model loading fails,
the implementation falls back to a safe template-based generator so the
project remains runnable in constrained environments.

The API is intentionally tiny: `generate_question(prompt, role, difficulty, keywords)`
returns a short question string.
"""
from __future__ import annotations

import os
import logging
from typing import Optional, List

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

QGEN_MODEL = os.getenv("QGEN_MODEL", "google/flan-t5-small")
_GEN_PIPE = None


def _get_pipeline():
    """Lazy-load and cache the transformers text-generation pipeline."""
    global _GEN_PIPE
    if _GEN_PIPE is not None:
        return _GEN_PIPE
    try:
        from transformers import pipeline

        print("loading model")
        _GEN_PIPE = pipeline("text-generation", model=QGEN_MODEL, device=-1)
        print("model loaded")
    except Exception as exc:
        log.info("transformers not available or generation failed: %s; falling back", exc)
        _GEN_PIPE = None
    return _GEN_PIPE


def _fallback_generate(role: str, history: List[str], last_answer: Optional[str], difficulty: Optional[str], keywords: Optional[List[str]]) -> str:
    # Very small template-based fallback. Keep question concise.
    base = "Tell me more about"
    if keywords:
        kw = ", ".join(keywords[:3])
        return f"Can you explain {kw} in the context of {role or 'this role'}?"
    if last_answer:
        short = last_answer.strip().split(".")[:1][0]
        return f"You mentioned '{short}'. Can you expand on that?"
    if difficulty == "hard":
        return f"Give a deep technical explanation relevant to {role or 'the role'}."
    if difficulty == "easy":
        return f"Explain the basic concepts of this topic for a junior candidate."
    return f"Please describe an example from your experience related to {role or 'the role'}."


def generate_question(role: str = "", history: Optional[List[str]] = None, last_answer: Optional[str] = None, difficulty: Optional[str] = None, keywords: Optional[List[str]] = None) -> str:
    """Generate a follow-up question.

    Parameters
    - role: candidate role (e.g., 'ml', 'frontend')
    - history: previous questions (optional)
    - last_answer: text of the candidate's previous answer (optional)
    - difficulty: suggested difficulty level ('easy','medium','hard')
    - keywords: list of detected keywords to focus on
    """
    history = history or []
    try:
        gen = _get_pipeline()
        if gen is None:
            raise RuntimeError("LLM pipeline unavailable")

        prompt_parts = [f"You are an interviewer for the role: {role or 'general'}."]
        if history:
            prompt_parts.append("Previous questions: " + " | ".join(history[-5:]))
        if last_answer:
            prompt_parts.append("Candidate answered: " + (last_answer[:500] + ("..." if len(last_answer) > 500 else "")))
        if keywords:
            prompt_parts.append("Focus on: " + ", ".join(keywords[:10]))
        if difficulty:
            prompt_parts.append("Difficulty: " + difficulty)

        prompt_parts.append("Ask one concise follow-up question that tests depth and understanding.")
        prompt = "\n".join(prompt_parts)

        out = gen(prompt, max_length=64, num_return_sequences=1)
        if out and isinstance(out, list) and out[0].get("generated_text"):
            text = out[0]["generated_text"]
            # Heuristic: split on newline and return the last sentence
            for line in reversed(text.splitlines()):
                line = line.strip()
                if len(line) > 10:
                    return line
        return _fallback_generate(role, history or [], last_answer, difficulty, keywords)
    except Exception as exc:
        log.info("transformers not available or generation failed: %s; falling back", exc)
        return _fallback_generate(role, history or [], last_answer, difficulty, keywords)


def generate_llm_question(role: str = "", history: Optional[List[str]] = None, last_answer: Optional[str] = None, difficulty: Optional[str] = None, keywords: Optional[List[str]] = None) -> str:
    """Alias for compatibility: explicit LLM-backed question generator."""
    return generate_question(role=role, history=history, last_answer=last_answer, difficulty=difficulty, keywords=keywords)


if __name__ == "__main__":
    print(generate_question("ml", ["Tell me about CNN"], "CNN is used for images, pooling and conv layers", "medium", ["convolution", "pooling"]))
