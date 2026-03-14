#!/usr/bin/env python3
"""Simple demo runner for AI Interview Trainer.

Usage:
    python scripts/run_demo.py path/to/video.mp4

The script calls the project's async wrapper for the inference pipeline and
prints the returned scores and feedback. It is defensive: missing files and
inference errors are handled and printed, and the pipeline's safe fallback
result will be displayed if inference fails.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Dict

# Ensure project root is on sys.path so top-level packages (pipelines, cv_models,
# ai_models, etc.) can be imported when this script is executed directly.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from pipelines.async_pipeline import run_async
except Exception as exc:  # pragma: no cover - defensive import for demo
    print("Failed to import pipeline runner:", exc)
    raise


DEFAULT_RESULT: Dict[str, Any] = {
    "emotion_score": 0.0,
    "eye_score": 0.0,
    "posture_score": 0.0,
    "final_score": 0.0,
    "feedback": [],
}


def pretty_print_result(res: Dict[str, Any]) -> None:
    """Print the inference result in a human-friendly format."""
    emotion = res.get("emotion_score", 0.0)
    eye = res.get("eye_score", 0.0)
    posture = res.get("posture_score", 0.0)
    final = res.get("final_score", 0.0)
    feedback = res.get("feedback", []) or []

    print(f"Emotion score: {float(emotion):.3f}")
    print(f"Eye score:     {float(eye):.3f}")
    print(f"Posture score: {float(posture):.3f}")
    print(f"Final score:   {float(final):.3f}")
    print("Feedback:")
    if not feedback:
        print(" - (no feedback)")
    else:
        for f in feedback:
            print(f" - {f}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/run_demo.py path/to/video.mp4")
        return 2

    video_path = Path(argv[1])
    if not video_path.exists():
        print(f"File not found: {video_path}")
        return 3

    print(f"Running demo on: {video_path}")

    try:
        result = run_async(str(video_path))
        if not isinstance(result, dict):
            print("Unexpected result from pipeline, showing fallback")
            result = DEFAULT_RESULT
    except Exception as exc:  # pragma: no cover - runtime errors may vary
        print("Inference failed with exception:", exc)
        result = DEFAULT_RESULT

    pretty_print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
