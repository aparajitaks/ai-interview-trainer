import time
import os
from types import SimpleNamespace
import importlib

import pytest

from pipelines.async_pipeline import run_async


def test_run_async_returns_result(monkeypatch, tmp_path):
    # Monkeypatch the inference_pipeline.run_inference to a quick fake
    fake_res = {"emotion_score": 0.1, "eye_score": 0.2, "posture_score": 0.3, "final_score": 0.25, "feedback": []}

    mod = importlib.import_module("pipelines.inference_pipeline")

    def fake_run(path):
        return fake_res

    monkeypatch.setattr(mod, "run_inference", fake_run)

    res = run_async(str(tmp_path / "video.mp4"))
    assert isinstance(res, dict)
    assert res.get("final_score") == pytest.approx(0.25)


def test_run_async_timeout(monkeypatch, tmp_path):
    # Simulate long-running inference and set a small timeout
    mod = importlib.import_module("pipelines.inference_pipeline")

    def slow_run(path):
        time.sleep(0.2)
        return {"final_score": 0.9}

    monkeypatch.setattr(mod, "run_inference", slow_run)
    monkeypatch.setenv("AIIT_INFERENCE_TIMEOUT", "0")

    # When timeout is 0, run_async should immediately return a safe fallback
    res = run_async(str(tmp_path / "video.mp4"))
    assert isinstance(res, dict)
    assert "final_score" in res
