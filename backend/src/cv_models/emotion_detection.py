"""
emotion_detection.py
--------------------
MediaPipe FaceLandmarker blendshape-based emotion classifier — V2.

Uses the MediaPipe Tasks API (FaceLandmarker with ``output_face_blendshapes=True``)
to obtain 52 facial blendshape coefficient scores per frame.  These coefficients
are more accurate and semantically richer than raw landmark geometry because
the model was trained end-to-end to separate expression units.

Key blendshapes used
~~~~~~~~~~~~~~~~~~~~
| Emotion  | Blendshapes averaged                           |
|----------|------------------------------------------------|
| Happy    | mouthSmileLeft + mouthSmileRight               |
| Sad      | mouthFrownLeft + mouthFrownRight               |
| Angry    | browDownLeft  + browDownRight                  |
| Surprise | browInnerUp   + jawOpen                        |
| Neutral  | default (no dominant expression)              |

Throttling
~~~~~~~~~~
``FaceLandmarker.detect_for_video`` is called every
``EmotionConfig.inference_interval`` frames.  The last cached result is
returned (``is_cached=True``) on skipped frames.

Timestamps
~~~~~~~~~~
VIDEO mode requires a monotonically increasing timestamp in milliseconds.
The detector tracks elapsed time from construction using ``time.time()``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from src.utils.config import EmotionConfig, ModelConfig
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
        "Emotion detection will be unavailable."
    )

# ---------------------------------------------------------------------------
# Blendshape name constants (MediaPipe FaceLandmarker v1 model)
# ---------------------------------------------------------------------------

_BS_SMILE_L  = "mouthSmileLeft"
_BS_SMILE_R  = "mouthSmileRight"
_BS_FROWN_L  = "mouthFrownLeft"
_BS_FROWN_R  = "mouthFrownRight"
_BS_BROW_D_L = "browDownLeft"
_BS_BROW_D_R = "browDownRight"
_BS_BROW_UP  = "browInnerUp"
_BS_JAW_OPEN = "jawOpen"

# Classification thresholds (blendshape score 0.0–1.0)
_HAPPY_THRESH    = 0.25
_SAD_THRESH      = 0.20
_ANGRY_THRESH    = 0.30
_SURPRISE_THRESH = 0.25   # both browInnerUp AND jawOpen must clear this


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class EmotionResult:
    """Holds the emotion classification output for one processed frame."""

    label: str
    """Dominant emotion label: ``"Happy"``, ``"Sad"``, ``"Angry"``, ``"Surprise"``, ``"Neutral"``."""

    confidence: float
    """Blendshape-derived score in [0.0, 1.0]."""

    is_cached: bool
    """``True`` when this result was returned from the throttle cache."""


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class EmotionDetectorLoadError(RuntimeError):
    """Raised when the emotion detector model cannot be loaded."""


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class EmotionDetector:
    """
    MediaPipe FaceLandmarker blendshape emotion classifier.

    Parameters
    ----------
    config : EmotionConfig
    model_config : ModelConfig
        Provides the path to ``face_landmarker.task``.

    Notes
    -----
    * Uses the Tasks API VIDEO running mode for temporal smoothing.
    * Call :meth:`close` when done to release MediaPipe resources.
    """

    def __init__(self, config: EmotionConfig, model_config: ModelConfig) -> None:
        if not _MP_AVAILABLE:
            raise EmotionDetectorLoadError(
                "MediaPipe is not installed. Run: pip install mediapipe"
            )

        model_path = Path(model_config.face_landmarker_path)
        if not model_path.exists():
            raise EmotionDetectorLoadError(
                f"FaceLandmarker model not found at '{model_path}'. "
                "Download with:\n"
                "  curl -L https://storage.googleapis.com/mediapipe-models/"
                "face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
                " -o models/face_landmarker.task"
            )

        self._config = config
        self._frame_counter: int = 0
        self._start_time: float = time.time()
        self._last_result = EmotionResult(
            label="Neutral", confidence=0.6, is_cached=False
        )

        opts = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=False,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
        logger.info(
            "EmotionDetector initialised (FaceLandmarker blendshapes, interval=%d).",
            config.inference_interval,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_emotion(
        self,
        frame: np.ndarray,
        face_box: Optional[Tuple[int, int, int, int]] = None,
    ) -> EmotionResult:
        """
        Classify emotion from facial blendshapes in the given BGR frame.

        Parameters
        ----------
        frame : np.ndarray
            Full BGR uint8 webcam frame.
        face_box : (x, y, w, h) | None
            Reserved for interface compatibility. Not used (FaceLandmarker
            locates the face internally).

        Returns
        -------
        EmotionResult
        """
        self._frame_counter += 1

        # Throttle: return cached result on non-inference frames
        if self._frame_counter % self._config.inference_interval != 0:
            return EmotionResult(
                label=self._last_result.label,
                confidence=self._last_result.confidence,
                is_cached=True,
            )

        try:
            label, confidence = self._classify(frame)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Emotion classification error (non-fatal): %s", exc)
            return EmotionResult(
                label=self._last_result.label,
                confidence=self._last_result.confidence,
                is_cached=True,
            )

        result = EmotionResult(label=label, confidence=confidence, is_cached=False)
        if confidence >= self._config.confidence_threshold:
            self._last_result = result
            logger.debug("Emotion: %s (conf=%.2f)", label, confidence)

        return result

    def close(self) -> None:
        """Release MediaPipe FaceLandmarker resources."""
        try:
            self._landmarker.close()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _classify(self, frame: np.ndarray) -> Tuple[str, float]:
        """Run FaceLandmarker and classify from blendshapes."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - self._start_time) * 1000)

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        if not result.face_blendshapes:
            logger.debug("EmotionDetector: no face blendshapes detected.")
            return "Neutral", 0.50

        # Build a lookup: blendshape_name → score
        bs: dict[str, float] = {
            c.category_name: c.score
            for c in result.face_blendshapes[0]
        }

        # Compute composite scores
        happy_score    = (_bs(bs, _BS_SMILE_L) + _bs(bs, _BS_SMILE_R)) / 2
        sad_score      = (_bs(bs, _BS_FROWN_L) + _bs(bs, _BS_FROWN_R)) / 2
        angry_score    = (_bs(bs, _BS_BROW_D_L) + _bs(bs, _BS_BROW_D_R)) / 2
        brow_up        = _bs(bs, _BS_BROW_UP)
        jaw_open       = _bs(bs, _BS_JAW_OPEN)
        surprise_score = min(brow_up, jaw_open)   # both must be elevated

        logger.debug(
            "Blendshapes — happy=%.2f sad=%.2f angry=%.2f surprise=%.2f",
            happy_score, sad_score, angry_score, surprise_score,
        )

        # Priority: Happy > Surprise > Angry > Sad > Neutral
        if happy_score >= _HAPPY_THRESH:
            return "Happy", round(min(1.0, happy_score / 0.6), 2)
        if surprise_score >= _SURPRISE_THRESH:
            return "Surprise", round(min(1.0, surprise_score / 0.5), 2)
        if angry_score >= _ANGRY_THRESH:
            return "Angry", round(min(1.0, angry_score / 0.6), 2)
        if sad_score >= _SAD_THRESH:
            return "Sad", round(min(1.0, sad_score / 0.5), 2)

        # Neutral: confidence inversely related to expression intensity
        max_expr = max(happy_score, sad_score, angry_score, surprise_score)
        neutral_conf = round(max(0.40, 0.85 - max_expr * 2), 2)
        return "Neutral", neutral_conf


def _bs(lookup: dict[str, float], name: str) -> float:
    """Safe blendshape score lookup (returns 0.0 if key absent)."""
    return lookup.get(name, 0.0)
