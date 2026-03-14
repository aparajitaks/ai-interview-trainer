"""Posture scorer using pose landmarks.

Exposes compute_posture_score(landmarks) which consumes a sequence of
pose landmarks (MediaPipe style) and returns a float score in [0.0, 1.0]
representing overall posture quality based on shoulder alignment and
head tilt. The module is defensive and logs errors instead of raising so
it can be used in production inference pipelines.
"""
from __future__ import annotations

import math
from typing import Sequence, Optional

import numpy as np

from utils.logger import get_logger

log = get_logger(__name__)


def _get_point(landmarks: Sequence, idx: int) -> Optional[np.ndarray]:
    """Safely extract a 2D point (x,y) from landmarks at index idx.

    Supports objects with .x/.y, sequences/tuples (x,y,...) or numpy arrays.
    Returns None if index missing or values invalid.
    """
    try:
        lm = landmarks[idx]
    except Exception:
        return None

    # Named attributes (object with .x/.y)
    x = None
    y = None
    try:
        x = getattr(lm, "x", None)
        y = getattr(lm, "y", None)
    except Exception:
        x = None
        y = None

    # Dict-style landmarks (e.g., from cv_models.pose_detector.detect_pose)
    if (x is None or y is None) and isinstance(lm, dict):
        try:
            x = lm.get("x", None)
            y = lm.get("y", None)
        except Exception:
            x = None
            y = None

    if x is None or y is None:
        # Sequence/array style or tuple
        try:
            x = lm[0]
            y = lm[1]
        except Exception:
            return None

    try:
        return np.array([float(x), float(y)], dtype=float)
    except Exception:
        return None


def _angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Return unsigned angle in degrees between 2 vectors."""
    try:
        a = v1.astype(float)
        b = v2.astype(float)
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        cosang = float(np.dot(a, b) / denom)
        cosang = max(-1.0, min(1.0, cosang))
        return math.degrees(math.acos(cosang))
    except Exception:
        return 0.0


def compute_posture_score(landmarks: Sequence) -> float:
    """Compute posture score from pose landmarks.

    Expected landmarks are MediaPipe Pose landmarks (list-like). The
    function computes two sub-scores:
      - shoulder_alignment_score: how horizontal the shoulders are (0..1)
      - head_tilt_score: how aligned the head/nose is above the shoulders (0..1)

    Both scores are combined and returned as a single float in [0,1].
    On error or missing landmarks the function returns 0.0 and logs a
    helpful message. The function never raises.
    """
    try:
        # MediaPipe Pose indices: 11 = left_shoulder, 12 = right_shoulder, 0 = nose
        left_sh = _get_point(landmarks, 11)
        right_sh = _get_point(landmarks, 12)
        nose = _get_point(landmarks, 0)

        if left_sh is None or right_sh is None:
            log.debug("Shoulder landmarks missing; cannot compute posture score")
            return 0.0

        # Shoulder alignment: angle between shoulder vector and horizontal
        shoulder_vec = right_sh - left_sh
        horizontal = np.array([1.0, 0.0])
        shoulder_angle = abs(_angle_between(shoulder_vec, horizontal))

        # Map shoulder angle (degrees) to score: 0deg -> 1.0, >=30deg -> 0.0
        shoulder_score = 1.0 - min(1.0, shoulder_angle / 30.0)

        # Head tilt: vector from shoulders midpoint to nose, compare to vertical
        if nose is None:
            log.debug("Nose landmark missing; head tilt score set to 0.0")
            head_score = 0.0
        else:
            mid = (left_sh + right_sh) / 2.0
            head_vec = nose - mid
            # vertical upwards vector in image coordinates: negative y direction
            vertical = np.array([0.0, -1.0])
            head_angle = abs(_angle_between(head_vec, vertical))
            # Map head angle: <=10deg ->1.0, >=45deg ->0.0
            head_score = 1.0 - min(1.0, (head_angle - 0.0) / 45.0)
            # Clamp
            head_score = float(max(0.0, min(1.0, head_score)))

        # Combine with weights
        shoulder_weight = 0.6
        head_weight = 0.4
        combined = shoulder_weight * float(max(0.0, min(1.0, shoulder_score))) + head_weight * head_score
        combined = float(max(0.0, min(1.0, combined)))

        log.debug("Posture components - shoulder_angle=%.2f, shoulder_score=%.3f, head_score=%.3f, combined=%.3f",
                  shoulder_angle, shoulder_score, head_score, combined)
        return combined
    except Exception:
        log.exception("compute_posture_score failed")
        return 0.0


def _make_landmark(x, y):
    """Helper: returns a simple object with x,y attributes for testing."""
    class LM:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    return LM(x, y)


def test_main() -> None:
    """Simple test harness that runs a few synthetic cases.

    Prints scores for a well-aligned posture and a badly aligned posture.
    """
    # Create a landmarks list with at least 13 entries (so index 12 exists).
    # We'll fill with neutral placeholders then replace needed indices.
    base = [_make_landmark(0.5, 0.5) for _ in range(33)]

    # Good posture: shoulders level, nose above midpoint
    base_good = list(base)
    base_good[11] = _make_landmark(0.4, 0.6)  # left shoulder
    base_good[12] = _make_landmark(0.6, 0.6)  # right shoulder
    base_good[0] = _make_landmark(0.5, 0.4)   # nose

    # Bad posture: right shoulder much higher (tilted), nose forward/down
    base_bad = list(base)
    base_bad[11] = _make_landmark(0.4, 0.65)
    base_bad[12] = _make_landmark(0.6, 0.55)
    base_bad[0] = _make_landmark(0.55, 0.7)

    print("Good posture score:", compute_posture_score(base_good))
    print("Bad posture score:", compute_posture_score(base_bad))


if __name__ == "__main__":
    test_main()
