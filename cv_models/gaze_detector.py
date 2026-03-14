"""Gaze detector using MediaPipe Face Mesh.

Provides lightweight helpers to load a FaceMesh detector and compute a
per-frame gaze score in [0.0, 1.0]. The implementation is defensive and
logs errors instead of raising for runtime inference so callers can
degrade gracefully when MediaPipe is unavailable on the platform.
"""
from __future__ import annotations

import logging
import os
import glob
from typing import List, Optional

import cv2
import numpy as np

from utils.logger import get_logger

log = get_logger(__name__)

_gaze_detector = None


def load_gaze_detector(static_image_mode: bool = False, max_num_faces: int = 1, refine_landmarks: bool = True):
    """Load and cache a MediaPipe FaceMesh detector used for gaze estimation.

    Returns the detector object or raises ImportError if mediapipe is not
    available.
    """
    global _gaze_detector
    if _gaze_detector is not None:
        return _gaze_detector

    try:
        import mediapipe as mp
    except Exception as exc:  # pragma: no cover - platform dependent
        log.error("mediapipe not available for gaze detector: %s", exc)
        raise ImportError("mediapipe is required for gaze detection") from exc

    try:
        mp_face_mesh = mp.solutions.face_mesh
        detector = mp_face_mesh.FaceMesh(static_image_mode=static_image_mode, max_num_faces=max_num_faces, refine_landmarks=refine_landmarks)
        _gaze_detector = detector
        log.info("Loaded MediaPipe FaceMesh gaze detector (refine=%s)", refine_landmarks)
        return detector
    except Exception as exc:
        log.exception("Failed to initialize FaceMesh detector: %s", exc)
        raise RuntimeError("Failed to initialize FaceMesh detector") from exc


def _landmark_to_point(landmark, image_w: int, image_h: int):
    return np.array([landmark.x * image_w, landmark.y * image_h], dtype=float)


def detect_gaze(frame: np.ndarray, detector) -> Optional[float]:
    """Detect gaze for a single BGR frame using the provided detector.

    Returns a float score between 0.0 and 1.0 where 1.0 indicates strong
    forward gaze (good eye contact) and values near 0.0 indicate looking
    away. Returns None if detection failed for the frame.
    """
    if frame is None:
        log.warning("Empty frame passed to detect_gaze")
        return None

    try:
        import mediapipe as mp
    except Exception:
        log.error("mediapipe not available in detect_gaze")
        return None

    # MediaPipe expects RGB
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = detector.process(image_rgb)
    if not results.multi_face_landmarks:
        log.debug("No face landmarks detected in frame for gaze")
        return None

    # Use first face
    face_landmarks = results.multi_face_landmarks[0]
    h, w = frame.shape[:2]

    # Common iris indices used by MediaPipe (when refine_landmarks=True)
    # left iris: 468-472, right iris: 473-477
    try:
        lm = face_landmarks.landmark
        left_iris_idxs = list(range(468, 473))
        right_iris_idxs = list(range(473, 478))

        # Eye corner landmarks (approximate) from FaceMesh
        left_eye_idxs = [33, 133]
        right_eye_idxs = [362, 263]

        # Compute centers
        left_iris_pts = [_landmark_to_point(lm[i], w, h) for i in left_iris_idxs if i < len(lm)]
        right_iris_pts = [ _landmark_to_point(lm[i], w, h) for i in right_iris_idxs if i < len(lm)]
        left_eye_pts = [ _landmark_to_point(lm[i], w, h) for i in left_eye_idxs if i < len(lm)]
        right_eye_pts = [ _landmark_to_point(lm[i], w, h) for i in right_eye_idxs if i < len(lm)]

        if not left_iris_pts or not right_iris_pts or not left_eye_pts or not right_eye_pts:
            log.debug("Insufficient landmarks for gaze estimation")
            return None

        left_iris_center = np.mean(left_iris_pts, axis=0)
        right_iris_center = np.mean(right_iris_pts, axis=0)
        left_eye_center = np.mean(left_eye_pts, axis=0)
        right_eye_center = np.mean(right_eye_pts, axis=0)

        # Horizontal displacement of iris within eye region
        left_disp = left_iris_center[0] - left_eye_center[0]
        right_disp = right_iris_center[0] - right_eye_center[0]

        # Eye width (distance between eye corners)
        left_width = abs(left_eye_pts[1][0] - left_eye_pts[0][0]) if len(left_eye_pts) >= 2 else 1.0
        right_width = abs(right_eye_pts[1][0] - right_eye_pts[0][0]) if len(right_eye_pts) >= 2 else 1.0

        # Normalized displacements
        left_norm = left_disp / max(left_width, 1.0)
        right_norm = right_disp / max(right_width, 1.0)

        # We expect near-zero normalized displacement when looking forward
        # Map absolute normalized displacement to score in [0,1]
        left_score = 1.0 - min(1.0, abs(left_norm) * 2.0)
        right_score = 1.0 - min(1.0, abs(right_norm) * 2.0)

        gaze_score = float(np.clip((left_score + right_score) / 2.0, 0.0, 1.0))
        return gaze_score
    except Exception:
        log.exception("Gaze detection failed for frame")
        return None


def get_gaze_score(frames: List[np.ndarray]) -> float:
    """Compute an aggregated gaze score over a sequence of frames.

    The function loads a detector, runs per-frame gaze detection and
    returns the mean score across frames that produced a valid score. If
    no frames yield a valid score, returns 0.0.
    """
    try:
        detector = load_gaze_detector()
    except Exception:
        log.exception("Could not load gaze detector; returning 0.0")
        return 0.0

    scores = []
    for f in frames:
        try:
            s = detect_gaze(f, detector)
            if s is not None:
                scores.append(float(np.clip(s, 0.0, 1.0)))
        except Exception:
            log.exception("Failed to compute gaze for a frame; skipping")

    if not scores:
        log.debug("No valid gaze scores computed; returning 0.0")
        return 0.0

    return float(np.mean(scores))


def _find_first_frame_dir(frames_dir: str = None) -> Optional[str]:
    if frames_dir is None:
        frames_dir = os.path.join(os.getcwd(), "storage", "frames")
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    for p in patterns:
        files = glob.glob(os.path.join(frames_dir, p))
        if files:
            files.sort()
            return files[0]
    return None


def test_main(frames_dir: str = None) -> None:
    """Simple test harness that reads a sample frame and prints gaze score."""
    sample = _find_first_frame_dir(frames_dir)
    if sample is None:
        log.error("No image frames found to run gaze test")
        return

    frame = cv2.imread(sample)
    if frame is None:
        log.error("Failed to read sample frame: %s", sample)
        return

    try:
        detector = load_gaze_detector()
    except Exception as exc:
        log.error("Gaze detector not available: %s", exc)
        return

    score = detect_gaze(frame, detector)
    log.info("Gaze score for sample %s: %s", sample, score)


if __name__ == "__main__":
    test_main()
