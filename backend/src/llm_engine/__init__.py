"""
llm_engine — V5 AI Interviewer Engine
======================================

Replaces the fragmented LLM logic with a unified, modular engine
featuring cross-questioning, conversation memory, and structured prompts.

Public API
~~~~~~~~~~
  generate_opening(domain)         → str  (first question)
  generate_next_step(q, a, d, h)   → NextStepResult
  generate_final_summary(d, h)     → dict

  is_ready()                       → bool (LLM available?)
"""

from src.llm_engine.client import is_ready
from src.llm_engine.engine import (
    NextStepResult,
    generate_final_summary,
    generate_next_step,
    generate_opening,
)
from src.llm_engine.memory import RoundMemory, build_context, get_follow_up_depth

__all__ = [
    "is_ready",
    "generate_opening",
    "generate_next_step",
    "generate_final_summary",
    "NextStepResult",
    "RoundMemory",
    "build_context",
    "get_follow_up_depth",
]
