"""
eye_contact.py
--------------
MediaPipe Tasks API FaceLandmarker iris-based eye-contact detector — V2.

Uses the FaceLandmarker model (which returns 478 landmarks including 10 iris
landmarks when ``output_face_blendshapes`` is used with the full model) to
track iris position and determine whether the user is looking at the camera.

Algorithm
~~~~~~~~~
1. Run FaceLandmarker in VIDEO mode to get 478 face + iris landmarks.
2. For both eyes, locate the iris centre landmark and the inner/outer
   canthus (eye-corner) landmarks.
3. Compute the *normalised horizontal deviation* of each iris from the
   midpoint of its canthus pair.
4. Convert deviation → score: 1.0 = centred (eye contact), 0.0 = deviated.
5. Average left/right scores and push into a rolling smoothing window.
6. Threshold the smoothed score → boolean ``is_contact``.

Landmark indices (MediaPipe 478-point model)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Right eye (subject's right, screen left):
  Outer: 33  |  Inner: 133  |  Iris centre: 468

Left eye (subject's left, screen right):
  Outer: 362 |  Inner: 263  |  Iris centre: 473

Note: Iris landmarks 468–477 are always present in the FaceLandmarker model
(the model bundles its own iris tracker), so no separate ``refine_landmarks``
flag is needed unlike the legacy FaceMesh solutions API.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from src.utils.config import EyeContactConfig, ModelConfig
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
        "Eye contact detection will be unavailable."
    )


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class EyeContactResult:
    """Holds the eye contact analysis output for one frame."""

    score: float
    """
    Smoothed iris-centring score in [0.0, 1.0].
    1.0 = irises perfectly centred (direct camera gaze).
    0.0 = irises maximally deviated (looking away).
    """

    is_contact: bool
    """``True`` when ``score >= EyeContactConfig.contact_threshold``."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EyeContactDetectorLoadError(RuntimeError):
    """Raised when the FaceLandmarker model cannot be loaded."""


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class EyeContactDetector:
    """
    MediaPipe FaceLandmarker iris-based eye-contact detector.

    Parameters
    ----------
    config : EyeContactConfig
    model_config : ModelConfig
        Provides the path to ``face_landmarker.task``.
    """

    # Landmark indices (right eye = subject's right = screen left)
    _R_IRIS:  int = 468
    _R_OUTER: int = 33
    _R_INNER: int = 133

    # Landmark indices (left eye = subject's left = screen right)
    _L_IRIS:  int = 473
    _L_OUTER: int = 362
    _L_INNER: int = 263

    def __init__(self, config: EyeContactConfig, model_config: ModelConfig) -> None:
        if not _MP_AVAILABLE:
            raise EyeContactDetectorLoadError(
                "MediaPipe is not installed. Run: pip install mediapipe"
            )

        model_path = Path(model_config.face_landmarker_path)
        if not model_path.exists():
            raise EyeContactDetectorLoadError(
                f"FaceLandmarker model not found at '{model_path}'."
            )

        self._config = config
        self._start_time: float = time.time()
        self._history: deque[float] = deque(maxlen=config.smoothing_window)

        opts = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            min_face_detection_confidence=config.min_detection_confidence,
            min_face_presence_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
        logger.info(
            "EyeContactDetector initialised (window=%d, threshold=%.2f).",
            config.smoothing_window,
            config.contact_threshold,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_eye_contact(self, frame: np.ndarray) -> EyeContactResult:
        """
        Analyse iris position in the given BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            Full BGR uint8 webcam frame.

        Returns
        -------
        EyeContactResult
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - self._start_time) * 1000)

        try:
            result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as exc:  # noqa: BLE001
            logger.debug("EyeContactDetector inference error: %s", exc)
            self._history.append(0.0)
            return self._smoothed_result()

        if not result.face_landmarks:
            logger.debug("EyeContactDetector: no face landmarks detected.")
            self._history.append(0.0)
            return self._smoothed_result()

        landmarks = result.face_landmarks[0]    # list of NormalizedLandmark

        try:
            raw_score = self._compute_iris_score(landmarks)
        except (IndexError, ZeroDivisionError, ValueError) as exc:
            logger.debug("Iris score computation error: %s", exc)
            raw_score = 0.0

        self._history.append(raw_score)
        logger.debug(
            "Eye contact raw=%.3f  smoothed=%.3f",
            raw_score, self._smoothed_score(),
        )
        return self._smoothed_result()

    def close(self) -> None:
        """Release MediaPipe FaceLandmarker resources."""
        try:
            self._landmarker.close()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_iris_score(self, landmarks) -> float:
        """Average left and right iris deviation scores."""
        right = self._iris_deviation_score(
            outer=landmarks[self._R_OUTER],
            inner=landmarks[self._R_INNER],
            iris=landmarks[self._R_IRIS],
        )
        left = self._iris_deviation_score(
            outer=landmarks[self._L_OUTER],
            inner=landmarks[self._L_INNER],
            iris=landmarks[self._L_IRIS],
        )
        return (right + left) / 2.0

    def _iris_deviation_score(self, outer, inner, iris) -> float:
        """
        Return [0.0, 1.0] for how centred the iris is in the eye socket.

        Landmarks are MediaPipe NormalizedLandmark objects with `.x`, `.y`.
        All coordinates are in [0.0, 1.0] image space.
        """
        eye_width = abs(inner.x - outer.x)
        if eye_width < 1e-6:
            return 0.5   # degenerate / partially occluded eye

        eye_center_x = (outer.x + inner.x) / 2.0
        deviation    = abs(iris.x - eye_center_x) / eye_width

        # Linear ramp: 0 deviation → 1.0; deviation >= threshold → 0.0
        return max(0.0, 1.0 - deviation / self._config.iris_deviation_threshold)

    def _smoothed_score(self) -> float:
        if not self._history:
            return 0.0
        return sum(self._history) / len(self._history)

    def _smoothed_result(self) -> EyeContactResult:
        smoothed   = self._smoothed_score()
        is_contact = smoothed >= self._config.contact_threshold
        return EyeContactResult(score=round(smoothed, 3), is_contact=is_contact)
