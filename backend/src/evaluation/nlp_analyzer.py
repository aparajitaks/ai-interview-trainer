"""
nlp_analyzer.py
---------------
Pure-Python NLP analysis — no external ML models, no API calls.

Three orthogonal dimensions:
  • Relevance   – Does the answer address the question?
  • Completeness – Is the answer thorough and well-supported?
  • Clarity     – Is the answer easy to follow?

Each function returns an integer score 0–100.
All logic is deterministic and explainable — ideal for auditing.
"""

from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Stop words — stripped before keyword analysis
# ---------------------------------------------------------------------------

_STOP = frozenset({
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","shall","can","not",
    "no","nor","so","yet","both","either","each","few","more","most","other",
    "some","such","that","this","these","those","then","than","too","very",
    "just","how","what","when","where","which","who","why","i","you","he",
    "she","we","they","it","my","your","his","her","our","its","their","me",
    "him","us","them","myself","yourself","himself","herself","itself",
    "ourselves","themselves","also","as","if","about","by","from","up","into",
    "through","during","before","after","above","below","between","out","off",
    "over","under","again","further","once","here","there","all","any","only",
    "own","same","s","t","re","ve","ll","d",
})

# ---------------------------------------------------------------------------
# Lightweight suffix-stripping stemmer
# ---------------------------------------------------------------------------
#
# Order matters — apply longer suffixes first to avoid over-stripping.
# Minimum stem length: 4 characters (avoids "be" → "b" etc.)

_SUFFIXES = [
    "isation", "ization", "ational", "tional",
    "encing", "ancing", "essing", "ishing",
    "alities", "ations", "nesses",
    "ication", "ments", "ating", "alism",
    "ising", "izing", "ising",
    "ously", "ating",
    "ingly", "edly",
    "ance", "ence", "ment", "ness", "tion", "sion",
    "ing", "ied", "ies", "ion",
    "ed", "er", "ly", "al",
    "s",
]

def _stem(word: str) -> str:
    """Strip common English suffixes to reduce inflectional variants."""
    w = word
    for suffix in _SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= 4:
            return w[: -len(suffix)]
    return w


# Filler / hedge words penalised in clarity
_FILLERS = frozenset({
    "um","uh","er","ah","like","basically","literally","honestly","actually",
    "obviously","clearly","simply","just","really","very","quite","pretty",
    "sort of","kind of","you know","i mean","i think","i feel","i guess",
    "to be honest","at the end of the day","needless to say",
})

# Domain terms that signal technical depth (bonus in completeness + relevance)
_TECH_TERMS = frozenset({
    # ML / AI
    "accuracy","precision","recall","f1","roc","auc","loss","gradient",
    "backpropagation","overfitting","underfitting","regularisation","regularization",
    "dropout","batch","epoch","learning rate","optimizer","adam","sgd",
    "transformer","attention","bert","llm","gpt","neural","cnn","rnn","lstm",
    "dataset","training","validation","cross-validation","pipeline",
    "feature","embedding","vector","matrix","tensor","recommendation",
    "collaborative","filtering","quantization","quantisation","onnx","drift",
    "inference","model","deploy","deployment","production","retrain",
    "classification","regression","clustering","fine-tuning","distillation",
    # Software / Systems
    "latency","throughput","scalable","microservice","api","rest","database",
    "sql","nosql","redis","docker","kubernetes","container","ci","cd",
    "monitoring","uptime","sla","cache","queue","async","concurrent",
    "algorithm","complexity","recursion","tree","graph","hash","heap",
    # Engineering practices
    "agile","scrum","sprint","stakeholder","requirement","architecture","design",
    "test","unit test","integration","refactor","code review","version control",
    "git","debugging","profiling","optimis","benchmark",
})

# STAR / example signal phrases (bonus in completeness)
_EXAMPLE_MARKERS = re.compile(
    r'\b(for example|for instance|such as|specifically|in particular|'
    r'i (implemented|built|designed|developed|deployed|created|led|solved|'
    r'reduced|increased|improved|achieved|containeris|monitor)|'
    r'the result was|this resulted in|which led to|'
    r'situation|task|action|result)\b',
    re.IGNORECASE,
)

_NUMBER_PATTERN = re.compile(
    r'\b\d+[\.,]?\d*\s*(%|percent|x|times|ms|seconds?|hours?|days?|k|m|gb|tb|requests?)?\b',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tokenisation helper
# ---------------------------------------------------------------------------

def _tokens(text: str, remove_stop: bool = True, stem: bool = False) -> list:
    words = re.findall(r"[a-z']+", text.lower())
    if remove_stop:
        words = [w for w in words if w not in _STOP]
    if stem:
        words = [_stem(w) for w in words]
    return words


def _sentences(text: str) -> list:
    return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]


# ---------------------------------------------------------------------------
# 1. Relevance  (0–100)
# ---------------------------------------------------------------------------

def evaluate_relevance(question: str, answer: str) -> tuple:
    """
    Score how well the answer addresses the question.

    Method
    ------
    * Extract stemmed keywords from the question.
    * Count what fraction appear (stemmed) in the answer.
    * Apply a bonus for tech terms present in the answer.

    Returns (score, explanation_note).
    """
    q_stemmed = set(_tokens(question, stem=True))
    a_stemmed = set(_tokens(answer,   stem=True))

    if not q_stemmed:
        return 50, "Could not extract question keywords."

    overlap = len(q_stemmed & a_stemmed)
    base    = overlap / len(q_stemmed)                      # 0.0 – 1.0

    # Bonus: tech terms present in answer (substring match for compound terms)
    lower_answer   = answer.lower()
    tech_in_answer = sum(1 for t in _TECH_TERMS if t in lower_answer)
    tech_bonus     = min(0.25, tech_in_answer * 0.04)       # up to +25 pts

    raw   = min(1.0, base * 1.5 + tech_bonus)
    score = int(round(raw * 100))

    if score >= 75:
        note = "Answer addresses the question well."
    elif score >= 50:
        note = "Answer partially addresses the question."
    elif score >= 30:
        note = "Answer is loosely related to the question."
    else:
        note = "Answer seems off-topic."

    return score, note


# ---------------------------------------------------------------------------
# 2. Completeness  (0–100)
# ---------------------------------------------------------------------------

def evaluate_completeness(answer: str) -> Tuple[int, str]:
    """
    Score depth and support — does the candidate back claims with evidence?

    Signals
    -------
    * Word count  (longer → more complete, up to ~200 words)
    * Specific numbers / metrics
    * STAR / example markers
    * Technical vocabulary
    """
    words    = _tokens(answer, remove_stop=False)
    wc       = len(words)

    # Word-count base (logarithmic — rewards depth without penalising brevity too harshly)
    wc_score = min(60, int(math.log1p(wc) / math.log1p(200) * 60)) if wc else 0

    # Bonus: quantitative evidence (numbers with units)
    num_matches   = len(_NUMBER_PATTERN.findall(answer))
    number_bonus  = min(15, num_matches * 5)

    # Bonus: STAR / example phrases
    example_hits  = len(_EXAMPLE_MARKERS.findall(answer))
    example_bonus = min(15, example_hits * 5)

    # Bonus: tech vocabulary density
    lower_answer  = answer.lower()
    tech_hits     = sum(1 for t in _TECH_TERMS if t in lower_answer)
    tech_bonus    = min(10, tech_hits * 2)

    score = min(100, wc_score + number_bonus + example_bonus + tech_bonus)

    if score >= 75:
        note = "Answer is thorough with specific evidence."
    elif score >= 50:
        note = "Answer covers the basics but could use more detail."
    elif score >= 30:
        note = "Answer is brief — try adding examples and metrics."
    else:
        note = "Answer is very short or lacks supporting detail."

    return score, note


# ---------------------------------------------------------------------------
# 3. Clarity  (0–100)
# ---------------------------------------------------------------------------

def evaluate_clarity(answer: str) -> Tuple[int, str]:
    """
    Score how easy the answer is to understand.

    Signals
    -------
    * Sentence length (target: 10–25 words — too long = unclear)
    * Vocabulary diversity (type-token ratio)
    * Filler / hedge word density
    """
    sentences = _sentences(answer)
    all_words = _tokens(answer, remove_stop=False)
    wc        = len(all_words)

    if wc < 5:
        return 20, "Answer is too short to assess clarity."

    # Sentence length score
    avg_len = wc / max(len(sentences), 1)
    if 8 <= avg_len <= 22:
        len_score = 40
    elif avg_len < 8:
        len_score = 25    # too choppy
    else:
        # gradually penalise very long sentences
        len_score = max(10, int(40 - (avg_len - 22) * 1.5))

    # Vocabulary diversity (type-token ratio, scaled)
    unique  = len(set(w.lower() for w in all_words))
    ttr     = unique / wc
    div_score = int(min(30, ttr * 60))

    # Filler penalty
    lower = answer.lower()
    filler_count = sum(
        len(re.findall(r'\b' + re.escape(f) + r'\b', lower))
        for f in _FILLERS
    )
    filler_penalty = min(20, filler_count * 4)

    score = max(0, len_score + div_score - filler_penalty)

    if score >= 70:
        note = "Answer is clear and well-structured."
    elif score >= 50:
        note = "Answer is mostly clear with minor verbosity."
    elif score >= 30:
        note = "Answer could be more concise and structured."
    else:
        note = "Answer is hard to follow — try shorter sentences."

    return score, note


# ---------------------------------------------------------------------------
# Batch analysis for a Q&A pair
# ---------------------------------------------------------------------------

def analyze_round(question: str, answer: str) -> Dict[str, object]:
    """Run all three analyses on a single Q&A pair and return a summary dict."""
    rel,  rel_note  = evaluate_relevance(question, answer)
    comp, comp_note = evaluate_completeness(answer)
    clar, clar_note = evaluate_clarity(answer)
    return {
        "relevance":         rel,
        "completeness":      comp,
        "clarity":           clar,
        "relevance_note":    rel_note,
        "completeness_note": comp_note,
        "clarity_note":      clar_note,
    }
