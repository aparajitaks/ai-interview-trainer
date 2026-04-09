"""
face_detection.py
-----------------
Haar Cascade face detector for the AI Interview Trainer.

Responsibility: load the Haar Cascade XML model once at construction time
and expose a single ``detect_faces`` method that returns typed bounding boxes.
All model-specific logic (scale, neighbours, min-size) is driven by
:class:`~src.utils.config.FaceDetectionConfig` — no magic numbers here.

Extending to DNN / MTCNN
~~~~~~~~~~~~~~~~~~~~~~~~~
When you graduate past Haar Cascades, create a new class (e.g.
``DNNFaceDetector``) that satisfies the same ``detect_faces`` interface.
``main.py`` only knows about that interface, so switching is a one-line swap.
"""

from __future__ import annotations

from typing import List, Tuple

import cv2
import numpy as np

from src.utils.config import FaceDetectionConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Bounding box type alias: (x, y, w, h) in pixel coordinates.
BoundingBox = Tuple[int, int, int, int]


class FaceDetectorLoadError(RuntimeError):
    """Raised when the Haar Cascade XML file cannot be located or loaded."""


class FaceDetector:
    """
    Haar Cascade-based face detector.

    The classifier XML is shipped with OpenCV; this class locates it at
    runtime so the project stays dependency-lightweight (no separate model
    download step).

    Parameters
    ----------
    config:
        A :class:`~src.utils.config.FaceDetectionConfig` instance.

    Example
    -------
    .. code-block:: python

        detector = FaceDetector(FaceDetectionConfig())
        boxes = detector.detect_faces(frame)
        for (x, y, w, h) in boxes:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    """

    _CASCADE_FILE = "haarcascade_frontalface_default.xml"

    def __init__(self, config: FaceDetectionConfig) -> None:
        self._config = config
        self._classifier = self._load_classifier()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_classifier(self) -> cv2.CascadeClassifier:
        """
        Locate and load the bundled Haar Cascade XML.

        Returns
        -------
        cv2.CascadeClassifier
            A loaded (ready-to-use) cascade classifier.

        Raises
        ------
        FaceDetectorLoadError
            If OpenCV's data directory cannot be found, or the XML
            file fails to load for any reason.
        """
        cascade_path: str = cv2.data.haarcascades + self._CASCADE_FILE  # type: ignore[attr-defined]
        logger.debug("Loading Haar Cascade from: %s", cascade_path)

        classifier = cv2.CascadeClassifier()
        if not classifier.load(cascade_path):
            raise FaceDetectorLoadError(
                f"Could not load Haar Cascade from '{cascade_path}'. "
                "This usually means OpenCV's data assets are missing. "
                "Try reinstalling opencv-python."
            )

        logger.info("Haar Cascade classifier loaded successfully.")
        return classifier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_faces(self, frame: np.ndarray) -> List[BoundingBox]:
        """
        Run face detection on a single BGR frame.

        The frame is converted to grayscale internally (and histogram-
        equalised) for better cascade performance under varying lighting.
        The colour frame is never mutated.

        Parameters
        ----------
        frame:
            A ``uint8`` BGR NumPy array as returned by ``cv2.VideoCapture``.

        Returns
        -------
        List[BoundingBox]
            A (possibly empty) list of ``(x, y, w, h)`` tuples, one per
            detected face, in pixel coordinates.
        """
        if frame is None or frame.size == 0:
            logger.warning("detect_faces() received an empty frame — skipping.")
            return []

        # Grayscale conversion + histogram equalisation improve detection
        # under poor or uneven lighting conditions.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        detections = self._classifier.detectMultiScale(
            gray,
            scaleFactor=self._config.scale_factor,
            minNeighbors=self._config.min_neighbors,
            minSize=self._config.min_size,
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        if len(detections) == 0:
            return []

        # ``detectMultiScale`` returns an ndarray of shape (N, 4) when it
        # finds faces, or an empty tuple when it finds none.  We normalise
        # to a typed list of tuples for downstream code.
        boxes: List[BoundingBox] = [
            (int(x), int(y), int(w), int(h)) for (x, y, w, h) in detections
        ]
        logger.debug("Detected %d face(s) in frame.", len(boxes))
        return boxes
