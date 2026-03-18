"""Simple keyword detection utilities for adaptive interview logic.

This module provides a lightweight, dependency-free way to detect
presence of important keywords in an answer text. The detector uses
per-role keyword lists (configurable) and returns detected keywords and
a coarse strength label (weak/medium/strong) used to guide difficulty.
"""
from __future__ import annotations

import re
from typing import List, Tuple, Dict

# Minimal per-role keyword hints: extend as needed.
ROLE_KEYWORDS: Dict[str, List[str]] = {
    "ml": ["convolution", "gradient", "overfitting", "regularization", "loss", "backprop", "epochs", "batch"],
    "frontend": ["react", "dom", "css", "accessibility", "performance", "a11y", "responsive", "webpack"],
    "backend": ["api", "scaling", "database", "consistency", "transactions", "caching", "kafka", "auth"],
    "dsa": ["algorithm", "complexity", "dp", "recursion", "binary", "graph", "sorting", "search"],
    "data": ["statistics", "regression", "classification", "pandas", "etl", "features", "imputation"],
}


def detect_keywords(role: str, answer_text: str) -> List[str]:
    if not answer_text:
        return []
    text = answer_text.lower()
    # build a keyword list: role-specific + global tokens from ROLE_KEYWORDS
    candidates = set(ROLE_KEYWORDS.get(role.lower(), []))
    # fallback to union of all if role unknown
    if not candidates:
        for v in ROLE_KEYWORDS.values():
            candidates.update(v)

    detected = []
    for kw in candidates:
        # simple word boundary match
        if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text):
            detected.append(kw)
    return detected


def strength_from_answer(answer_text: str, detected_keywords: List[str]) -> str:
    # Heuristic: use length + number of keywords
    if not answer_text or len(answer_text.strip()) < 20:
        return "weak"
    k = len(detected_keywords)
    l = len(answer_text.split())
    if k >= 3 and l > 40:
        return "strong"
    if k >= 1 and l > 20:
        return "medium"
    return "weak"
