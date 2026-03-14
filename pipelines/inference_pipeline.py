"""Inference pipeline for AI Interview Trainer.

Pipeline flow:
    video_path
    -> extract frames
    -> detect faces
    -> detect pose
    -> eye contact score
    -> emotion score
    -> metrics
    -> final score
    -> feedback

This module is headless-safe, uses logging, and returns a structured dict.
"""

from __future__ import annotations

import logging
import os
import glob
import tempfile
import shutil
from typing import Dict, List

from config.settings import STORAGE_DIR, LOG_LEVEL

import cv2
import numpy as np

from preprocessing.video_to_frames import video_to_frames

from cv_models.face_detector import load_face_detector, detect_faces
from cv_models.pose_detector import load_pose_detector, detect_pose, get_posture_score
from cv_models.eye_contact import get_eye_contact_score, estimate_eye_contact
from cv_models.emotion_model import get_emotion_model, get_emotion_score, predict_emotion

from evaluation import metrics as eval_metrics
from evaluation import scoring as eval_scoring
from evaluation import feedback_engine

log = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


# Default safe result to return on any early failure or empty input
DEFAULT_RESULT = {
    "emotion_score": 0.0,
    "eye_score": 0.0,
    "posture_score": 0.0,
    "final_score": 0.0,
    "feedback": [],
}


def _find_frames(dir_path: str) -> List[str]:
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    files: List[str] = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(dir_path, p)))
    files.sort()
    return files


def run_inference(video_path: str, fps: int = 2) -> Dict[str, object]:
    """Run the end-to-end inference pipeline on a video file.

    Returns a dict with keys: emotion_score, eye_score, posture_score, final_score, feedback
    """
    if not os.path.exists(video_path):
        log.error("Video not found: %s", video_path)
        return DEFAULT_RESULT.copy()

    tmp_dir = tempfile.mkdtemp(prefix="aiit_frames_")
    try:
        # Extract frames (writes into tmp_dir)
        log.info("Extracting frames to: %s", tmp_dir)
        video_to_frames(video_path, tmp_dir, fps=fps)

        frame_paths = _find_frames(tmp_dir)
        if not frame_paths:
            log.error("No frames extracted from video: %s", video_path)
            return DEFAULT_RESULT.copy()

        # Prepare models/detectors
        try:
            face_detector = load_face_detector()
        except Exception:
            log.error("Failed to load face detector", exc_info=True)
            face_detector = None

        try:
            pose_detector = load_pose_detector()
        except Exception:
            log.error("Failed to load pose detector", exc_info=True)
            pose_detector = None

        try:
            emotion_model = get_emotion_model()
        except Exception:
            log.error("Failed to load emotion model", exc_info=True)
            emotion_model = None

        # Accumulators
        face_crops = []
        face_pairs = []  # (frame, bbox) for eye contact
        posture_scores = []

        for fp in frame_paths:
            frame = cv2.imread(fp)
            if frame is None:
                log.debug("Skipping unreadable frame: %s", fp)
                continue

            if face_detector is None:
                log.debug("No face detector available; skipping face detection")
                continue

            faces = detect_faces(frame, face_detector)
            if not faces:
                log.debug("No faces detected in frame: %s", fp)
                continue

            # Use first face for per-frame metrics; this keeps pipeline simple
            x, y, w, h = faces[0]
            # Defensive crop bounds
            h_img, w_img = frame.shape[:2]
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(w_img, x + w), min(h_img, y + h)
            if x1 >= x2 or y1 >= y2:
                log.debug("Invalid bbox on frame %s: %s", fp, faces[0])
                continue

            face_crop = frame[y1:y2, x1:x2]
            face_crops.append(face_crop)
            face_pairs.append((frame, (x1, y1, x2 - x1, y2 - y1)))

            # Pose detection (on whole frame) if available
            if pose_detector is not None:
                try:
                    landmarks = detect_pose(frame, pose_detector)
                except Exception:
                    log.error("Pose detection failed on frame (detect_pose): %s", fp, exc_info=True)
                    landmarks = None

                if landmarks:
                    try:
                        ps = get_posture_score(landmarks)
                        # Clamp and append
                        ps = float(np.clip(ps, 0.0, 1.0))
                    except Exception:
                        log.error("Posture scoring failed on frame (get_posture_score): %s", fp, exc_info=True)
                        ps = 0.0
                    posture_scores.append(ps)

        # Compute eye score using face_pairs (safe fallback if no faces)
        if not face_pairs:
            log.debug("No face pairs collected; setting eye_score to 0.0")
            eye_score_raw = 0.0
        else:
            try:
                eye_score_raw = get_eye_contact_score(face_pairs)
            except Exception:
                log.error("Eye contact computation failed", exc_info=True)
                eye_score_raw = 0.0

        # Compute emotion score using face crops and emotion_model (safe fallback if no faces)
        if not face_crops:
            log.debug("No face crops collected; setting emotion_score to 0.0")
            emotion_score_val = 0.0
        else:
            try:
                emotion_score_raw = get_emotion_score(face_crops, emotion_model)
                # get_emotion_score returns dict with label/confidence/details
                if isinstance(emotion_score_raw, dict):
                    emotion_score_val = float(emotion_score_raw.get("confidence", 0.0))
                else:
                    # For backward compat, allow direct float
                    emotion_score_val = float(emotion_score_raw or 0.0)
            except Exception:
                log.error("Emotion scoring failed", exc_info=True)
                emotion_score_val = 0.0

        # Posture aggregation: mean of posture_scores
        posture_score_raw = float(np.mean(posture_scores)) if posture_scores else 0.0

        # Clamp raw metrics to [0,1] to ensure numeric stability
        try:
            emotion_score_val = float(np.clip(emotion_score_val, 0.0, 1.0))
        except Exception:
            log.error("Failed to clamp emotion_score_val; defaulting to 0.0", exc_info=True)
            emotion_score_val = 0.0

        try:
            eye_score_raw = float(np.clip(eye_score_raw, 0.0, 1.0))
        except Exception:
            log.error("Failed to clamp eye_score_raw; defaulting to 0.0", exc_info=True)
            eye_score_raw = 0.0

        try:
            posture_score_raw = float(np.clip(posture_score_raw, 0.0, 1.0))
        except Exception:
            log.error("Failed to clamp posture_score_raw; defaulting to 0.0", exc_info=True)
            posture_score_raw = 0.0

        # Normalize metrics via evaluation.metrics
        emotion_metric = eval_metrics.compute_emotion_metric(emotion_score_val)
        eye_metric = eval_metrics.compute_eye_metric(eye_score_raw)
        posture_metric = eval_metrics.compute_posture_metric(posture_score_raw)

        # Final scoring
        final = eval_scoring.compute_final_score(emotion_metric, eye_metric, posture_metric)
        try:
            final = float(np.clip(final, 0.0, 1.0))
        except Exception:
            log.error("Failed to clamp final score; defaulting to 0.0", exc_info=True)
            final = 0.0

        # Feedback
        feedback = feedback_engine.generate_feedback(emotion_metric, eye_metric, posture_metric)

        result = {
            "emotion_score": float(np.clip(emotion_metric, 0.0, 1.0)),
            "eye_score": float(np.clip(eye_metric, 0.0, 1.0)),
            "posture_score": float(np.clip(posture_metric, 0.0, 1.0)),
            "final_score": float(np.clip(final, 0.0, 1.0)),
            "feedback": feedback,
        }

        log.info("Inference result: %s", result)
        return result

    finally:
        # Cleanup extracted frames directory
        try:
            shutil.rmtree(tmp_dir)
            log.debug("Removed temporary frames directory: %s", tmp_dir)
        except Exception:
            log.exception("Failed to remove temporary directory: %s", tmp_dir)


if __name__ == "__main__":
    # Simple command-line test. Update the path below to a small sample video.
    sample_video = os.path.join(STORAGE_DIR, "sample.mp4")
    res = run_inference(sample_video)
    log.info("Run complete. Result: %s", res)
