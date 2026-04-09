"""
video_pipeline.py
-----------------
End-to-end video analysis pipeline for the AI Interview Trainer API.

Processes a list of sampled BGR frames through face / emotion / eye-contact /
posture detectors and aggregates results into a single ``AnalysisResult``.

Architecture
~~~~~~~~~~~~
* MediaPipe models run in **IMAGE mode** (not VIDEO mode) — each frame is
  processed independently with no temporal smoothing.  This is correct for
  batch video analysis where frames are not sequential in wall-clock time.
* All detector instances are created **once per** ``VideoAnalysisPipeline``
  and reused across every ``process()`` call.  In the FastAPI context this
  object lives in ``app.state`` for the lifetime of the server process,
  so model loading happens exactly once.
* The Haar cascade face detector is always active.  MediaPipe detectors are
  optional — if the model files are absent they are skipped gracefully.

Aggregation strategy
~~~~~~~~~~~~~~~~~~~~
| Metric           | Method                                              |
|------------------|-----------------------------------------------------|
| emotion          | Mode (most frequent label across all frames)        |
| eye_contact      | Mean iris-centring score × 100 → integer percent    |
| posture          | Mode (most frequent label across all frames)        |
| confidence_score | 40 % face-detection rate + 30 % eye-contact + 30 % good-posture rate |
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from src.cv_models.face_detection import FaceDetector
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Optional MediaPipe import
# ---------------------------------------------------------------------------

try:
    import mediapipe as mp
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False
    mp = None  # type: ignore[assignment]
    logger.warning(
        "MediaPipe not installed — emotion / eye-contact / posture "
        "detection will be skipped in the video pipeline."
    )

# ---------------------------------------------------------------------------
# Blendshape + landmark index constants
# ---------------------------------------------------------------------------

# Face blendshapes (emotion)
_BS_SMILE_L  = "mouthSmileLeft"
_BS_SMILE_R  = "mouthSmileRight"
_BS_FROWN_L  = "mouthFrownLeft"
_BS_FROWN_R  = "mouthFrownRight"
_BS_BROW_D_L = "browDownLeft"
_BS_BROW_D_R = "browDownRight"
_BS_BROW_UP  = "browInnerUp"
_BS_JAW_OPEN = "jawOpen"

# Emotion thresholds
_HAPPY_THRESH = 0.25
_SAD_THRESH   = 0.20
_ANGRY_THRESH = 0.30
_SURP_THRESH  = 0.25

# Iris landmark indices (FaceLandmarker 478-point model)
_R_IRIS,  _R_OUTER, _R_INNER = 468, 33,  133
_L_IRIS,  _L_OUTER, _L_INNER = 473, 362, 263

# Pose landmark indices
_NOSE, _L_SH, _R_SH = 0, 11, 12


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class FrameResult:
    """Per-frame analysis output."""

    frame_index:       int   = 0
    has_face:          bool  = False
    emotion:           Optional[str]   = None
    eye_contact_score: float = 0.0     # 0.0–1.0
    posture:           Optional[str]   = None


@dataclass
class AnalysisResult:
    """Aggregated analysis across all processed frames (API response body)."""

    emotion:          str = "Neutral"
    eye_contact:      int = 0           # 0–100 percentage
    posture:          str = "Unknown"
    confidence_score: int = 0           # 0–100 composite quality score
    frames_processed: int = 0
    frames_with_face: int = 0

    def to_dict(self) -> dict:
        return {
            "emotion":          self.emotion,
            "eye_contact":      self.eye_contact,
            "posture":          self.posture,
            "confidence_score": self.confidence_score,
            "frames_processed": self.frames_processed,
            "frames_with_face": self.frames_with_face,
        }


# ---------------------------------------------------------------------------
# Internal IMAGE-mode MediaPipe wrappers
# ---------------------------------------------------------------------------


class _FaceLandmarkerImage:
    """FaceLandmarker in IMAGE mode — one call per frame, no timestamps."""

    def __init__(self, model_path: Path, blendshapes: bool = True) -> None:
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
            output_face_blendshapes=blendshapes,
            output_facial_transformation_matrixes=False,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._lm = mp_vision.FaceLandmarker.create_from_options(opts)

    def detect(self, rgb: np.ndarray):
        return self._lm.detect(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        )

    def close(self) -> None:
        try:
            self._lm.close()
        except Exception:  # noqa: BLE001
            pass


class _PoseLandmarkerImage:
    """PoseLandmarker in IMAGE mode — one call per frame, no timestamps."""

    def __init__(self, model_path: Path) -> None:
        opts = mp_vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._lm = mp_vision.PoseLandmarker.create_from_options(opts)

    def detect(self, rgb: np.ndarray):
        return self._lm.detect(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        )

    def close(self) -> None:
        try:
            self._lm.close()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Main pipeline class
# ---------------------------------------------------------------------------


class VideoAnalysisPipeline:
    """
    Stateful pipeline that processes video frames and aggregates results.

    Create once per server process — model loading is expensive.
    Re-use the same instance for every incoming ``/analyze-video`` request.

    Parameters
    ----------
    config : AppConfig
        Root configuration (provides model paths and detector thresholds).
    """

    def __init__(self, config: AppConfig) -> None:
        self._cfg = config

        logger.info("VideoAnalysisPipeline: initialising models …")

        # Haar face detector (always loaded — no extra model file)
        self._face_detector = FaceDetector(config.face_detection)

        # MediaPipe IMAGE-mode detectors — optional
        self._face_lm: Optional[_FaceLandmarkerImage] = None
        self._pose_lm: Optional[_PoseLandmarkerImage] = None

        if _MP_AVAILABLE:
            face_path = Path(config.models.face_landmarker_path)
            pose_path = Path(config.models.pose_landmarker_path)

            if face_path.exists():
                self._face_lm = _FaceLandmarkerImage(face_path, blendshapes=True)
                logger.info("FaceLandmarker (IMAGE mode) loaded from %s", face_path.name)
            else:
                logger.warning(
                    "face_landmarker.task not found at '%s'. "
                    "Emotion and eye-contact detection disabled.",
                    face_path,
                )

            if pose_path.exists():
                self._pose_lm = _PoseLandmarkerImage(pose_path)
                logger.info("PoseLandmarker LITE (IMAGE mode) loaded from %s", pose_path.name)
            else:
                logger.warning(
                    "pose_landmarker_lite.task not found at '%s'. "
                    "Posture detection disabled.",
                    pose_path,
                )

        logger.info("VideoAnalysisPipeline: ready.")

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def process(self, frames: List[np.ndarray]) -> AnalysisResult:
        """
        Analyse a list of BGR frames and return an aggregated result.

        Parameters
        ----------
        frames : List[np.ndarray]
            Sampled BGR uint8 frames extracted from the uploaded video.

        Returns
        -------
        AnalysisResult
        """
        if not frames:
            logger.warning("process() received an empty frame list.")
            return AnalysisResult()

        frame_results: List[FrameResult] = []

        for idx, frame in enumerate(frames):
            fr = self._process_frame(frame, idx)
            frame_results.append(fr)
            logger.debug(
                "Frame %3d: face=%-5s emo=%-8s eye=%.2f pst=%s",
                idx, fr.has_face, fr.emotion or "—",
                fr.eye_contact_score, fr.posture or "—",
            )

        return self._aggregate(frame_results)

    def close(self) -> None:
        """Release all MediaPipe model resources."""
        if self._face_lm:
            self._face_lm.close()
        if self._pose_lm:
            self._pose_lm.close()
        logger.info("VideoAnalysisPipeline: resources released.")

    # ------------------------------------------------------------------
    # Private — per-frame logic
    # ------------------------------------------------------------------

    def _process_frame(self, frame: np.ndarray, idx: int) -> FrameResult:
        result = FrameResult(frame_index=idx)

        # ── Haar face detector ─────────────────────────────────────────
        boxes = self._face_detector.detect_faces(frame)
        result.has_face = len(boxes) > 0

        # ── MediaPipe (optional) ───────────────────────────────────────
        if not _MP_AVAILABLE or self._face_lm is None:
            return result

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Emotion + eye contact from FaceLandmarker
        try:
            face_res = self._face_lm.detect(rgb)
            if face_res.face_blendshapes:
                result.emotion = self._classify_emotion(face_res.face_blendshapes[0])
            if face_res.face_landmarks:
                result.eye_contact_score = self._iris_score(face_res.face_landmarks[0])
        except Exception as exc:  # noqa: BLE001
            logger.debug("FaceLandmarker error frame %d: %s", idx, exc)

        # Posture from PoseLandmarker
        if self._pose_lm is not None:
            try:
                pose_res = self._pose_lm.detect(rgb)
                if pose_res.pose_landmarks:
                    result.posture = self._classify_posture(pose_res.pose_landmarks[0])
            except Exception as exc:  # noqa: BLE001
                logger.debug("PoseLandmarker error frame %d: %s", idx, exc)

        return result

    # ------------------------------------------------------------------
    # Private — emotion (blendshapes)
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_emotion(blendshapes) -> str:
        bs = {c.category_name: c.score for c in blendshapes}
        happy    = (bs.get(_BS_SMILE_L, 0) + bs.get(_BS_SMILE_R, 0)) / 2
        sad      = (bs.get(_BS_FROWN_L, 0) + bs.get(_BS_FROWN_R, 0)) / 2
        angry    = (bs.get(_BS_BROW_D_L, 0) + bs.get(_BS_BROW_D_R, 0)) / 2
        surprise = min(bs.get(_BS_BROW_UP, 0), bs.get(_BS_JAW_OPEN, 0))

        if happy    >= _HAPPY_THRESH: return "Happy"
        if surprise >= _SURP_THRESH:  return "Surprise"
        if angry    >= _ANGRY_THRESH: return "Angry"
        if sad      >= _SAD_THRESH:   return "Sad"
        return "Neutral"

    # ------------------------------------------------------------------
    # Private — eye contact (iris deviation score)
    # ------------------------------------------------------------------

    @staticmethod
    def _iris_score(landmarks) -> float:
        def _dev(outer, inner, iris) -> float:
            w = abs(inner.x - outer.x)
            if w < 1e-6:
                return 0.5
            cx  = (outer.x + inner.x) / 2.0
            dev = abs(iris.x - cx) / w
            return max(0.0, 1.0 - dev / 0.28)

        right = _dev(
            landmarks[_R_OUTER], landmarks[_R_INNER], landmarks[_R_IRIS]
        )
        left  = _dev(
            landmarks[_L_OUTER], landmarks[_L_INNER], landmarks[_L_IRIS]
        )
        return (right + left) / 2.0

    # ------------------------------------------------------------------
    # Private — posture (shoulder + nose geometry)
    # ------------------------------------------------------------------

    def _classify_posture(self, landmarks) -> str:
        nose = landmarks[_NOSE]
        l_sh = landmarks[_L_SH]
        r_sh = landmarks[_R_SH]

        sh_dx = abs(r_sh.x - l_sh.x)
        sh_dy = abs(r_sh.y - l_sh.y)
        tilt  = (
            math.degrees(math.atan2(sh_dy, sh_dx)) if sh_dx > 1e-6 else 90.0
        )

        mid_x = (l_sh.x + r_sh.x) / 2.0
        mid_y = (l_sh.y + r_sh.y) / 2.0
        vec_x = nose.x - mid_x
        vec_y = mid_y  - nose.y   # positive when nose is above shoulders
        lean  = (
            abs(math.degrees(math.atan2(abs(vec_x), vec_y))) if vec_y > 0 else 90.0
        )

        cfg = self._cfg.posture
        if tilt > cfg.shoulder_tilt_threshold_deg:
            return "Leaning"
        if lean > cfg.slouch_angle_threshold_deg:
            return "Slouching"
        return "Good"

    # ------------------------------------------------------------------
    # Private — aggregation
    # ------------------------------------------------------------------

    def _aggregate(self, results: List[FrameResult]) -> AnalysisResult:
        total     = len(results)
        with_face = sum(1 for r in results if r.has_face)

        # Emotion — mode over frames that produced an emotion label
        emotions = [r.emotion for r in results if r.emotion is not None]
        dominant_emotion = (
            Counter(emotions).most_common(1)[0][0] if emotions else "Neutral"
        )

        # Eye contact — mean iris score → percentage
        eye_scores = [r.eye_contact_score for r in results]
        mean_eye   = sum(eye_scores) / len(eye_scores) if eye_scores else 0.0
        eye_pct    = int(round(mean_eye * 100))

        # Posture — mode over frames that produced a posture label
        postures = [r.posture for r in results if r.posture is not None]
        dominant_posture = (
            Counter(postures).most_common(1)[0][0] if postures else "Unknown"
        )

        # Confidence score — weighted combination of detection rates
        face_rate    = with_face / total if total > 0 else 0.0
        good_posture = (
            sum(1 for p in postures if p == "Good") / len(postures)
            if postures else 0.0
        )
        confidence = int(round(
            (0.40 * face_rate + 0.30 * mean_eye + 0.30 * good_posture) * 100
        ))

        logger.info(
            "Aggregation complete: emotion=%s eye=%d%% posture=%s "
            "confidence=%d  faces=%d/%d",
            dominant_emotion, eye_pct, dominant_posture,
            confidence, with_face, total,
        )

        return AnalysisResult(
            emotion          = dominant_emotion,
            eye_contact      = eye_pct,
            posture          = dominant_posture,
            confidence_score = confidence,
            frames_processed = total,
            frames_with_face = with_face,
        )
