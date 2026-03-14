"""Asynchronous wrapper around the inference pipeline using a thread pool.

Provides run_async(video_path) which runs the heavy inference call in a
background thread and returns the pipeline result. The implementation is
defensive: it logs errors, supports a configurable timeout via
AIIT_INFERENCE_TIMEOUT (seconds) and falls back to a safe default result
from the inference pipeline when errors/timeouts occur.
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from utils.logger import get_logger

log = get_logger(__name__)


def _safe_default() -> Dict[str, Any]:
    try:
        from pipelines import inference_pipeline

        return getattr(inference_pipeline, "DEFAULT_RESULT", {
            "emotion_score": 0.0,
            "eye_score": 0.0,
            "posture_score": 0.0,
            "final_score": 0.0,
            "feedback": "inference-failed",
        })
    except Exception:
        log.exception("Failed to import inference_pipeline for default result; using hard fallback")
        return {
            "emotion_score": 0.0,
            "eye_score": 0.0,
            "posture_score": 0.0,
            "final_score": 0.0,
            "feedback": "inference-failed-import",
        }


def run_async(video_path: str) -> Dict[str, Any]:
    """Run inference_pipeline.run_inference(video_path) in a background thread.

    Parameters
    - video_path: path to the video to analyze.

    Returns
    - result dict from inference_pipeline or a safe fallback on error/timeout.
    """
    try:
        from pipelines import inference_pipeline
    except Exception:
        log.exception("Could not import inference_pipeline; returning safe default")
        return _safe_default()

    timeout_s = int(os.getenv("AIIT_INFERENCE_TIMEOUT", "60"))

    log.info("Starting async inference for %s with timeout=%ss", video_path, timeout_s)

    with ThreadPoolExecutor(max_workers=1) as exe:
        future = exe.submit(inference_pipeline.run_inference, video_path)
        try:
            result = future.result(timeout=timeout_s)
            log.info("Async inference completed for %s", video_path)
            return result
        except FuturesTimeoutError:
            log.exception("Async inference timed out after %s seconds for %s", timeout_s, video_path)
            # Best-effort cancellation
            try:
                future.cancel()
            except Exception:
                log.debug("Failed to cancel future after timeout")
            return _safe_default()
        except Exception:
            log.exception("Async inference failed for %s", video_path)
            return _safe_default()


def _test_main():
    import argparse

    parser = argparse.ArgumentParser(description="Test async inference pipeline")
    parser.add_argument("video", nargs="?", default="storage/video/sample.mp4", help="path to video file")
    args = parser.parse_args()

    res = run_async(args.video)
    log.info("Async pipeline result: %s", res)
    print(res)


if __name__ == "__main__":
    _test_main()
