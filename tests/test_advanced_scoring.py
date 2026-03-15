import os
from evaluation.advanced_scoring import compute_score


def test_weight_normalization_and_clamp(monkeypatch):
    monkeypatch.setenv("AIIT_EMOTION_WEIGHT", "2")
    monkeypatch.setenv("AIIT_EYE_WEIGHT", "1")
    monkeypatch.setenv("AIIT_POSTURE_WEIGHT", "1")
    monkeypatch.delenv("AIIT_ROLE_WEIGHT", raising=False)

    val = compute_score(1.0, 1.0, 1.0)
    assert 0.99 <= val <= 1.0

    val2 = compute_score(10.0, 10.0, 10.0)
    assert abs(val2 - 1.0) < 1e-6


def test_role_weight(monkeypatch):
    monkeypatch.delenv("AIIT_EMOTION_WEIGHT", raising=False)
    monkeypatch.delenv("AIIT_EYE_WEIGHT", raising=False)
    monkeypatch.delenv("AIIT_POSTURE_WEIGHT", raising=False)
    monkeypatch.setenv("AIIT_ROLE_WEIGHT", "0.5")

    val = compute_score(0.8, 0.8, 0.8)
    assert abs(val - 0.4) < 0.02
