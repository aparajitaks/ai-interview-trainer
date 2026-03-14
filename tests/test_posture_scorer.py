import pytest
from cv_models.posture_scorer import compute_posture_score


def make_lm(idx, x, y):
    return {"index": idx, "x": x, "y": y}


def test_good_posture():
    # Construct landmarks list with dict-style entries expected by pose detector
    landmarks = [{} for _ in range(33)]
    # shoulders level
    landmarks[11] = make_lm(11, 0.4, 0.5)
    landmarks[12] = make_lm(12, 0.6, 0.5)
    # nose above midpoint
    landmarks[0] = make_lm(0, 0.5, 0.3)

    score = compute_posture_score(landmarks)
    assert score > 0.7, f"Expected good posture >0.7 got {score}"


def test_bad_posture():
    landmarks = [{} for _ in range(33)]
    # shoulders misaligned
    landmarks[11] = make_lm(11, 0.4, 0.6)
    landmarks[12] = make_lm(12, 0.6, 0.4)
    landmarks[0] = make_lm(0, 0.55, 0.7)

    score = compute_posture_score(landmarks)
    assert score < 0.4, f"Expected bad posture <0.4 got {score}"
