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

from config.settings import STORAGE_DIR, LOG_LEVEL, SAMPLE_FRAMES

import cv2
import numpy as np

from preprocessing.video_to_frames import video_to_frames

# Model loader and CV scorers
from ai_models.model_loader import get_emotion_model, get_pose_model
from cv_models.emotion_model import predict_emotion, get_emotion_score
from cv_models.face_detector import load_face_detector, detect_faces
from cv_models.pose_detector import detect_pose
from cv_models.gaze_detector import get_gaze_score
from cv_models.posture_scorer import compute_posture_score

from evaluation import advanced_scoring
from evaluation.feedback_generator import generate_feedback
import json
from datetime import datetime

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

        # Sample frames according to settings.SAMPLE_FRAMES
        try:
            total = len(frame_paths)
            n = max(1, int(SAMPLE_FRAMES))
            if total <= n:
                sampled_paths = frame_paths
            else:
                import numpy as _np

                idx = _np.linspace(0, total - 1, n, dtype=int)
                sampled_paths = [frame_paths[i] for i in idx]
        except Exception:
            log.exception("Frame sampling failed; falling back to all frames")
            sampled_paths = frame_paths

        # Prepare models/detectors
        try:
            face_detector = load_face_detector()
        except Exception:
            log.exception("Failed to load face detector")
            face_detector = None

        try:
            pose_detector = get_pose_model()
        except Exception:
            log.exception("Failed to load pose detector via model_loader")
            pose_detector = None

        try:
            emotion_model = get_emotion_model()
        except Exception:
            log.exception("Failed to load emotion model via model_loader")
            emotion_model = None

        # Accumulators
        face_crops = []
        sampled_frames = []
        posture_scores = []

        for fp in sampled_paths:
            frame = cv2.imread(fp)
            if frame is None:
                log.debug("Skipping unreadable frame: %s", fp)
                continue
            # Collect sampled frames for gaze/emotion
            sampled_frames.append(frame)

            # Face detection + crop for emotion
            try:
                if face_detector is None:
                    log.debug("No face detector available; skipping face detection for emotion")
                else:
                    faces = detect_faces(frame, face_detector)
                    if faces:
                        x, y, w, h = faces[0]
                        h_img, w_img = frame.shape[:2]
                        x1, y1 = max(0, x), max(0, y)
                        x2, y2 = min(w_img, x + w), min(h_img, y + h)
                        if x1 < x2 and y1 < y2:
                            face_crop = frame[y1:y2, x1:x2]
                            face_crops.append(face_crop)
            except Exception:
                log.exception("Face detection/cropping failed for frame: %s", fp)

            # Pose detection (on whole frame) if available
            if pose_detector is not None:
                try:
                    landmarks = detect_pose(frame, pose_detector)
                except Exception:
                    log.exception("Pose detection failed on frame (detect_pose): %s", fp)
                    landmarks = None

                if landmarks:
                    try:
                        ps = compute_posture_score(landmarks)
                        ps = float(np.clip(ps, 0.0, 1.0))
                    except Exception:
                        log.exception("Posture scoring failed on frame: %s", fp)
                        ps = 0.0
                    posture_scores.append(ps)

        # Compute eye score using sampled_frames
        try:
            eye_score_raw = get_gaze_score(sampled_frames)
        except Exception:
            log.exception("Gaze scoring failed; defaulting to 0.0")
            eye_score_raw = 0.0

        # Compute emotion score using face crops and emotion_model (safe fallback if no faces)
        if not face_crops or emotion_model is None:
            log.debug("No face crops or emotion model missing; setting emotion_score to 0.0")
            emotion_score_val = 0.0
        else:
            try:
                emotion_agg = get_emotion_score(face_crops, emotion_model)
                if isinstance(emotion_agg, dict):
                    emotion_score_val = float(emotion_agg.get("confidence", 0.0))
                else:
                    emotion_score_val = float(emotion_agg or 0.0)
            except Exception:
                log.exception("Emotion scoring failed")
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

        # Normalize/aggregate metrics via advanced scoring
        try:
            final = advanced_scoring.compute_score(emotion_score_val, eye_score_raw, posture_score_raw)
        except Exception:
            log.exception("Advanced scoring failed; defaulting final to 0.0")
            final = 0.0
        try:
            final = float(np.clip(final, 0.0, 1.0))
        except Exception:
            log.error("Failed to clamp final score; defaulting to 0.0", exc_info=True)
            final = 0.0

        # Feedback
        try:
            feedback = generate_feedback(
                float(np.clip(emotion_score_val, 0.0, 1.0)),
                float(np.clip(eye_score_raw, 0.0, 1.0)),
                float(np.clip(posture_score_raw, 0.0, 1.0)),
                float(np.clip(final, 0.0, 1.0)),
            )
        except Exception:
            log.exception("Feedback generation failed; returning empty feedback list")
            feedback = []
        result = {
            "emotion_score": float(np.clip(emotion_score_val, 0.0, 1.0)),
            "eye_score": float(np.clip(eye_score_raw, 0.0, 1.0)),
            "posture_score": float(np.clip(posture_score_raw, 0.0, 1.0)),
            "final_score": float(np.clip(final, 0.0, 1.0)),
            "feedback": feedback,
        }

        # Validate result contains all required keys. If any are missing,
        # return a safe DEFAULT_RESULT to avoid downstream KeyError or
        # schema mismatches. This preserves existing behavior while
        # guarding against regressions in the downstream model functions.
        required_keys = {"emotion_score", "eye_score", "posture_score", "final_score", "feedback"}
        if not required_keys.issubset(set(result.keys())):
            missing = required_keys - set(result.keys())
            log.error("Inference result missing keys: %s. Returning DEFAULT_RESULT", missing)
            return DEFAULT_RESULT.copy()

        # Persist result to storage/results/result_YYYYMMDD_HHMMSS.json for auditing
        try:
            results_base = os.path.dirname(STORAGE_DIR)
            results_dir = os.path.join(results_base, "results")
            os.makedirs(results_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            fname = f"result_{ts}.json"
            fpath = os.path.join(results_dir, fname)
            with open(fpath, "w", encoding="utf-8") as fh:
                json.dump(result, fh, indent=2)
            log.info("Saved inference result to %s", fpath)
        except Exception:
            log.exception("Failed to persist inference result to JSON file")

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
