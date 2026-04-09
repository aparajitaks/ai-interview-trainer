"""
video_capture.py
----------------
Webcam / video-source abstraction for the AI Interview Trainer.

Responsibility: open a capture device, validate it, expose frames one at a
time, and release all OS resources on shutdown — nothing more.

Design notes
~~~~~~~~~~~~
* Uses a context manager so callers never have to remember to call
  ``release()`` manually.
* Camera properties are configured once at open-time to avoid per-frame
  overhead.
* ``read_frame`` separates concerns: the pipeline loop just calls this
  method and never touches ``cv2.VideoCapture`` directly.
"""

from __future__ import annotations

import cv2
import numpy as np
from types import TracebackType
from typing import Optional, Tuple, Type

from src.utils.config import CameraConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CameraOpenError(RuntimeError):
    """Raised when the video capture device cannot be opened."""


class VideoCapture:
    """
    Thin, resource-safe wrapper around :class:`cv2.VideoCapture`.

    Parameters
    ----------
    config:
        A :class:`~src.utils.config.CameraConfig` instance that drives
        device selection and requested resolution / FPS.

    Example
    -------
    .. code-block:: python

        cfg = CameraConfig(index=0)
        with VideoCapture(cfg) as cap:
            while True:
                ok, frame = cap.read_frame()
                if not ok:
                    break
                # ... process frame ...
    """

    def __init__(self, config: CameraConfig) -> None:
        self._config = config
        self._cap: Optional[cv2.VideoCapture] = None

    # ------------------------------------------------------------------
    # Context-manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "VideoCapture":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> bool:
        self.release()
        # Returning False re-raises any exception that occurred in the body.
        return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self) -> None:
        """
        Open the capture device and apply the requested camera properties.

        Raises
        ------
        CameraOpenError
            If ``cv2.VideoCapture`` fails to open the device or the device
            reports itself as not opened after construction.
        """
        logger.info(
            "Opening camera device (index=%d, %dx%d @ %d fps).",
            self._config.index,
            self._config.frame_width,
            self._config.frame_height,
            self._config.fps,
        )

        cap = cv2.VideoCapture(self._config.index)

        if not cap.isOpened():
            raise CameraOpenError(
                f"Failed to open camera at index {self._config.index}. "
                "Ensure a webcam is connected and not in use by another process."
            )

        # Request preferred resolution / FPS.  Hardware may silently ignore
        # unsupported values, which is acceptable behaviour.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.frame_height)
        cap.set(cv2.CAP_PROP_FPS, self._config.fps)

        actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        logger.info(
            "Camera opened successfully. Actual resolution: %dx%d @ %.1f fps.",
            actual_w,
            actual_h,
            actual_fps,
        )

        self._cap = cap

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Capture the next frame from the device.

        Returns
        -------
        (success, frame):
            ``success`` is ``True`` when a valid frame was decoded.
            ``frame`` is a ``uint8`` BGR NumPy array on success, ``None``
            on failure (e.g. device disconnected mid-session).
        """
        if self._cap is None:
            logger.error("read_frame() called before open(). Call open() first.")
            return False, None

        ret, frame = self._cap.read()
        if not ret:
            logger.warning("Failed to read frame — device may be disconnected.")
            return False, None

        return True, frame

    def release(self) -> None:
        """
        Release the underlying :class:`cv2.VideoCapture` and free OS resources.

        Safe to call multiple times; subsequent calls are no-ops.
        """
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()
            logger.info("Camera device released.")
        self._cap = None

    # ------------------------------------------------------------------
    # Convenience properties (read-only, reflect actual camera values)
    # ------------------------------------------------------------------

    @property
    def frame_size(self) -> Tuple[int, int]:
        """Return the actual ``(width, height)`` reported by the device."""
        if self._cap is None:
            return (0, 0)
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return (w, h)

    @property
    def is_open(self) -> bool:
        """``True`` if the capture device is currently open."""
        return self._cap is not None and self._cap.isOpened()
