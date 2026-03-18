from __future__ import annotations

import logging
from typing import Any, Dict

log = logging.getLogger(__name__)


class FeedbackGenerator:
    """Generate structured feedback for an interview answer.

    Attempts to use HuggingFace transformers (google/flan-t5-small). If not
    available or generation fails, falls back to a deterministic heuristic
    using the numeric scores and detected keywords.
    """

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipe = None
        try:
            from transformers import pipeline

            # Lazy load pipeline; model will be downloaded on first use.
            self.pipe = pipeline("text2text-generation", model="google/flan-t5-small")
        except Exception as exc:
            log.info("Transformers pipeline not available or failed to load: %s", exc)
            self.pipe = None

    def generate_feedback(self, role: str | None, answer: Dict[str, Any]) -> Dict[str, Any]:
        """Return a dict with keys: strengths, weaknesses, suggestions, final_rating.

        answer is expected to have keys: score, emotion_score, posture_score,
        eye_score, answer_text, keywords.
        """
        # Normalize input
        score = float(answer.get("score") or 0.0)
        emotion = float(answer.get("emotion_score") or 0.0)
        posture = float(answer.get("posture_score") or 0.0)
        eye = float(answer.get("eye_score") or 0.0)
        text = answer.get("answer_text") or ""
        keywords = answer.get("keywords") or []

        # Try LLM generation if available
        if self.pipe is not None:
            try:
                prompt = self._build_prompt(role, score, emotion, posture, eye, text, keywords)
                out = self.pipe(prompt, max_length=256, do_sample=False)
                if out and isinstance(out, list) and "generated_text" in out[0]:
                    gen = out[0]["generated_text"]
                    # Attempt to parse JSON from the model output
                    import json

                    try:
                        parsed = json.loads(gen)
                        # Ensure expected keys exist
                        if all(k in parsed for k in ("strengths", "weaknesses", "suggestions", "final_rating")):
                            return parsed
                    except Exception:
                        # Not valid JSON — fall back to wrapping the generated text
                        return {
                            "strengths": [gen[:200]],
                            "weaknesses": [],
                            "suggestions": [],
                            "final_rating": round(score * 5, 2),
                        }
            except Exception:
                log.exception("LLM feedback generation failed; falling back to heuristic")

        # Heuristic fallback
        return self._heuristic_feedback(role, score, emotion, posture, eye, text, keywords)

    def _build_prompt(self, role, score, emotion, posture, eye, text, keywords) -> str:
        data = {
            "role": role or "",
            "score": score,
            "emotion_score": emotion,
            "posture_score": posture,
            "eye_score": eye,
            "answer_text": text,
            "keywords": keywords,
        }
        # Ask the model to return a JSON dict with specific fields
        prompt = (
            "You are an expert interview coach. Given the following answer metadata, produce a JSON object with keys:\n"
            "strengths (list of short bullet points), weaknesses (list of short bullet points), suggestions (list of short actionable suggestions),\n"
            "and final_rating (a number between 0 and 5).\n\n"
            f"Input: {data}\n\n"
            "Return only valid JSON. Keep lists short (max 4 items each)." 
        )
        return prompt

    def _heuristic_feedback(self, role, score, emotion, posture, eye, text, keywords) -> Dict[str, Any]:
        strengths = []
        weaknesses = []
        suggestions = []

        avg = (score + emotion + posture + eye) / 4.0 if True else score

        if score >= 0.75:
            strengths.append("Answer content was relevant and on-topic")
        elif score >= 0.5:
            strengths.append("Partially addressed the question; could be more specific")
        else:
            weaknesses.append("Answer lacked clear structure or relevant examples")

        if emotion >= 0.6:
            strengths.append("Displayed appropriate emotional expressiveness")
        else:
            weaknesses.append("Tone or expressiveness was flat; try varying intonation")

        if posture >= 0.6:
            strengths.append("Good posture during the answer")
        else:
            weaknesses.append("Posture could be improved — sit/stand straight and avoid slouching")

        if eye >= 0.6:
            strengths.append("Maintained good eye contact")
        else:
            weaknesses.append("Work on eye contact — look toward the camera more consistently")

        if keywords:
            suggestions.append("Incorporate these keywords if relevant: " + ", ".join(keywords[:5]))

        if not text.strip():
            weaknesses.append("Provide a brief summary of your answer next time to make intent clear")
            suggestions.append("Start with a one-sentence summary, then provide 1-2 supporting details or examples")

        # final rating mapped from avg (0..1) to 0..5
        final_rating = round(max(0.0, min(1.0, avg)) * 5.0, 2)

        # Limit list sizes
        strengths = strengths[:4]
        weaknesses = weaknesses[:4]
        suggestions = suggestions[:4]

        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "final_rating": final_rating,
        }


# Module-level singleton for convenience
_GEN = None


def get_generator() -> FeedbackGenerator:
    global _GEN
    if _GEN is None:
        _GEN = FeedbackGenerator()
    return _GEN
