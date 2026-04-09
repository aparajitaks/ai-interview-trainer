"""
posture_detection.py
--------------------
MediaPipe Tasks API PoseLandmarker-based posture analyser — V2.

Classifies sitting posture as "Good", "Slouching", or "Leaning" using the
geometric relationship between nose and shoulder landmarks detected by the
MediaPipe PoseLandmarker LITE model.

Algorithm
~~~~~~~~~
1. Run PoseLandmarker in VIDEO mode (LITE complexity for real-time speed).
2. Extract three key landmarks in normalised image coordinates [0, 1]:
      Nose  (index 0)
      Left shoulder  (index 11)
      Right shoulder (index 12)
3. **Shoulder tilt** — angle of the shoulder line from horizontal.
   Above ``PostureConfig.shoulder_tilt_threshold_deg`` → "Leaning".
4. **Vertical lean** — angle of the nose-to-shoulder-midpoint vector from
   true vertical.  Above ``PostureConfig.slouch_angle_threshold_deg`` → "Slouching".
5. Classification priority: Leaning > Slouching > Good.

Why normalised coordinates?
~~~~~~~~~~~~~~~~~~~~~~~~~~~
All measurements are relative to normalised [0, 1] image space, making the
thresholds resolution-agnostic — they work the same at 720p and 1080p.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.utils.config import PostureConfig, ModelConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guard
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
        "MediaPipe not found. Install with: pip install mediapipe. "
        "Posture detection will return 'Unknown'."
    )


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class PostureResult:
    """Holds the posture analysis output for one frame."""

    label: str
    """``"Good"``, ``"Slouching"``, ``"Leaning"``, or ``"Unknown"``."""

    shoulder_tilt_deg: float
    """Absolute tilt of the shoulder line from horizontal (degrees)."""

    vertical_lean_deg: float
    """Deviation of the nose-to-shoulder-midpoint vector from vertical (deg)."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class PostureDetectorLoadError(RuntimeError):
    """Raised when the PoseLandmarker model cannot be loaded."""


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class PostureDetector:
    """
    MediaPipe Tasks API PoseLandmarker posture classifier.

    Parameters
    ----------
    config : PostureConfig
    model_config : ModelConfig
        Provides the path to ``pose_landmarker_lite.task``.

    Notes
    -----
    * Call :meth:`close` when done to release MediaPipe resources.
    """

    # MediaPipe Pose landmark indices (same as legacy solutions API)
    _NOSE:           int = 0
    _LEFT_SHOULDER:  int = 11
    _RIGHT_SHOULDER: int = 12

    def __init__(self, config: PostureConfig, model_config: ModelConfig) -> None:
        if not _MP_AVAILABLE:
            raise PostureDetectorLoadError(
                "MediaPipe is not installed. Run: pip install mediapipe"
            )

        model_path = Path(model_config.pose_landmarker_path)
        if not model_path.exists():
            raise PostureDetectorLoadError(
                f"PoseLandmarker model not found at '{model_path}'. "
                "Download with:\n"
                "  curl -L https://storage.googleapis.com/mediapipe-models/"
                "pose_landmarker/pose_landmarker_lite/float16/latest/"
                "pose_landmarker_lite.task -o models/pose_landmarker_lite.task"
            )

        self._config = config
        self._start_time: float = time.time()

        opts = mp_vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=config.min_detection_confidence,
            min_pose_presence_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(opts)
        logger.info(
            "PostureDetector initialised (PoseLandmarker LITE, complexity=%d).",
            config.model_complexity,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_posture(self, frame: np.ndarray) -> PostureResult:
        """
        Analyse posture in the given BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            Full BGR uint8 webcam frame.

        Returns
        -------
        PostureResult
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - self._start_time) * 1000)

        try:
            result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as exc:  # noqa: BLE001
            logger.debug("PostureDetector inference error: %s", exc)
            return PostureResult(label="Unknown", shoulder_tilt_deg=0.0, vertical_lean_deg=0.0)

        if not result.pose_landmarks:
            logger.debug("Pose: no landmarks detected.")
            return PostureResult(label="Unknown", shoulder_tilt_deg=0.0, vertical_lean_deg=0.0)

        try:
            return self._classify(result.pose_landmarks[0])
        except Exception as exc:  # noqa: BLE001
            logger.debug("Posture classification error: %s", exc)
            return PostureResult(label="Unknown", shoulder_tilt_deg=0.0, vertical_lean_deg=0.0)

    def close(self) -> None:
        """Release MediaPipe PoseLandmarker resources."""
        try:
            self._landmarker.close()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _classify(self, landmarks) -> PostureResult:
        """
        Compute geometry from three key landmarks and classify posture.

        MediaPipe normalised coordinates: x ∈ [0, 1] left→right,
        y ∈ [0, 1] top→bottom (y increases downward).
        """
        nose  = landmarks[self._NOSE]
        l_sh  = landmarks[self._LEFT_SHOULDER]
        r_sh  = landmarks[self._RIGHT_SHOULDER]

        # ── Shoulder tilt ──────────────────────────────────────────────
        # In a face-on camera view, body-right shoulder (lm 12) appears on
        # the screen-LEFT → r_sh.x < l_sh.x → raw sh_dx is negative.
        # Using abs() on both components keeps the result in [0°, 90°]:
        # 0° = perfectly level shoulders, 90° = one shoulder directly above.
        sh_dx = abs(r_sh.x - l_sh.x)   # horizontal span  (always positive)
        sh_dy = abs(r_sh.y - l_sh.y)   # vertical drop     (always positive)
        shoulder_tilt_deg = math.degrees(math.atan2(sh_dy, sh_dx))

        # ── Vertical lean ──────────────────────────────────────────────
        # Vector from shoulder midpoint to nose.
        # Flip y so "nose above shoulders" gives vec_y > 0.
        mid_x = (l_sh.x + r_sh.x) / 2.0
        mid_y = (l_sh.y + r_sh.y) / 2.0
        vec_x = nose.x - mid_x
        vec_y = mid_y - nose.y   # positive when nose is above shoulder midpoint

        if vec_y <= 0:
            vertical_lean_deg = 90.0   # extreme forward lean or off-screen
        else:
            vertical_lean_deg = abs(math.degrees(math.atan2(abs(vec_x), vec_y)))

        # ── Classification (Leaning > Slouching > Good) ────────────────
        cfg = self._config
        if shoulder_tilt_deg > cfg.shoulder_tilt_threshold_deg:
            label = "Leaning"
        elif vertical_lean_deg > cfg.slouch_angle_threshold_deg:
            label = "Slouching"
        else:
            label = "Good"

        logger.debug(
            "Posture: %s  tilt=%.1f°  lean=%.1f°",
            label, shoulder_tilt_deg, vertical_lean_deg,
        )
        return PostureResult(
            label=label,
            shoulder_tilt_deg=round(shoulder_tilt_deg, 1),
            vertical_lean_deg=round(vertical_lean_deg, 1),
        )
