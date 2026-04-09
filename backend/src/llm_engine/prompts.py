"""
prompts.py
----------
Structured prompt templates for the V5 AI Interviewer.

All prompts are f-string templates that accept keyword arguments
via `str.format()`.  The module exposes builder functions rather
than raw strings so that callers never need to know the template
internals.

Prompt design goals
~~~~~~~~~~~~~~~~~~~
* Deterministic structure — JSON output with exact keys.
* Cross-questioning logic embedded in the prompt rules.
* Context-aware — receives windowed conversation history.
* Role-adaptive — adjusts technical depth to the domain.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# System-level persona
# ---------------------------------------------------------------------------

SYSTEM_PERSONA = (
    "You are an expert technical interviewer at a top-tier technology company. "
    "You conduct focused, respectful, and progressively challenging interviews. "
    "You adapt your questions based on the candidate's responses. "
    "You probe deeper when answers are vague or incomplete. "
    "You are direct and concise. You never repeat a question."
)


# ---------------------------------------------------------------------------
# Opening question
# ---------------------------------------------------------------------------

_OPENING_TEMPLATE = """{persona}

You are interviewing a candidate for the role: {domain}.

Generate ONE opening interview question that:
- Is warm but professional
- Sets the tone for a technical interview
- Gives the candidate a chance to introduce their relevant experience

Output ONLY the question text, no preamble or labels."""


def build_opening_prompt(domain: str) -> str:
    """Build the prompt for the first question of an interview."""
    return _OPENING_TEMPLATE.format(persona=SYSTEM_PERSONA, domain=domain)


# ---------------------------------------------------------------------------
# Next-step prompt (evaluate + decide + generate)
# ---------------------------------------------------------------------------

_NEXT_STEP_TEMPLATE = """{persona}

You are interviewing a candidate for: {domain}.

You are an expert interviewer for {domain}.

Evaluate this answer:
Question: {question}
Answer: {answer}

## Current Exchange
Question: {question}
Candidate's Answer: {answer}

## Recent Conversation Context
{history}

## Follow-Up Status
Follow-ups asked on this topic so far: {follow_up_count}
Maximum follow-ups allowed per topic: 2

## Instructions

Evaluate the candidate's answer and decide the next step.
Also generate an ideal expected answer for the question, and compare it with the candidate's answer. Identify gaps and suggest improvements.
Keep explanations simple, clear, and concise for learning.

**Scoring rubric (0–10):**
- 0–2: No meaningful content, completely off-topic, or nonsensical
- 3–4: Vague, lacks specifics, partially relevant
- 5–6: Adequate but shallow, missing depth or examples
- 7–8: Good — clear, relevant, with some concrete details
- 9–10: Excellent — thorough, specific examples, strong technical depth

**Cross-questioning rules:**
- If score < 6 AND follow_up_count < 2: set needs_follow_up=true and ask a probing question that digs deeper into the WEAK area of the answer
- If score >= 6 OR follow_up_count >= 2: set needs_follow_up=false and move to a completely NEW topic
- Follow-up questions should NOT repeat the original question — they should probe a specific gap
- New-topic questions should progressively increase in difficulty

Return ONLY a valid JSON object with these exact keys:
{{
  "score": <integer 0-10>,
  "feedback": "<2-3 sentences: what was good, what was missing>",
  "expected_answer": "<ideal answer in 2-4 concise sentences>",
  "gap_analysis": "<plain-language gap between expected and candidate answer>",
  "improvement": "<specific next-step suggestion in 1-2 sentences>",
  "follow_up": <true or false>,
  "follow_up_reason": "<why deeper probing is needed, or null if moving on>",
  "next_question": "<the next question to ask the candidate>"
}}"""


def build_next_step_prompt(
    domain:          str,
    question:        str,
    answer:          str,
    history:         str,
    follow_up_count: int,
) -> str:
    """
    Build the combined evaluate-and-decide prompt.

    Parameters
    ----------
    domain          : job role / domain
    question        : the question that was just asked
    answer          : the candidate's answer
    history         : formatted conversation context (last 2-3 rounds)
    follow_up_count : how many follow-ups have been asked on this topic chain
    """
    return _NEXT_STEP_TEMPLATE.format(
        persona         = SYSTEM_PERSONA,
        domain          = domain,
        question        = question,
        answer          = answer,
        history         = history or "(This is the first question — no prior context.)",
        follow_up_count = follow_up_count,
    )


# ---------------------------------------------------------------------------
# Final summary prompt
# ---------------------------------------------------------------------------

_FINAL_SUMMARY_TEMPLATE = """{persona}

You just completed an interview with a candidate for: {domain}.

## Full Interview Transcript
{transcript}

## Per-Round Scores
{scores_summary}

Provide a comprehensive evaluation. Return ONLY a valid JSON object:
{{
  "summary": "<3-4 sentence overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<area 1>", "<area 2>", "<area 3>"],
  "overall_score": <integer 0-100>,
  "communication_score": <integer 0-100>,
  "technical_score": <integer 0-100>,
  "confidence_score": <integer 0-100>
}}"""


def build_final_summary_prompt(
    domain:     str,
    transcript: str,
    scores:     str,
) -> str:
    """Build the prompt for the final holistic evaluation."""
    return _FINAL_SUMMARY_TEMPLATE.format(
        persona        = SYSTEM_PERSONA,
        domain         = domain,
        transcript     = transcript,
        scores_summary = scores,
    )
