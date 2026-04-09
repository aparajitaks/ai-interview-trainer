"""
video_loader.py
---------------
OpenCV-based video file reader with configurable frame sampling.

Loads mp4 / mov / avi / mkv files and extracts frames at a target
sample rate (frames-per-second), so the ML pipeline only sees a
representative subset of frames rather than every frame at 30 fps.

Design choices
~~~~~~~~~~~~~~
* Sampling is done by reading the video sequentially and keeping
  every Nth frame (``N = floor(video_fps / sample_fps)``).
  This is memory-efficient for long videos; frames are never all
  loaded into RAM simultaneously unless ``load_frames`` is called.
* ``iter_frames`` is the core primitive — all other methods build on it.
* A ``max_frames`` cap prevents runaway memory use for long uploads.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Generator, List, Tuple

import cv2
import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class VideoLoadError(ValueError):
    """Raised when a video cannot be opened, read, or is in a bad format."""


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VideoMetadata:
    """Intrinsic properties of the loaded video file."""

    width: int
    height: int
    fps: float
    total_frames: int
    duration_seconds: float


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class VideoLoader:
    """
    Reads a video file and yields sampled BGR frames.

    Parameters
    ----------
    path : str | Path
        Path to the video file.
    sample_fps : float
        Target sampling rate in frames per second.
        ``2.0`` → extract 2 frames per second of footage.
        Lower = faster but coarser analysis.
    max_frames : int
        Hard cap on extracted frames (prevents RAM exhaustion for long videos).

    Example
    -------
    .. code-block:: python

        loader = VideoLoader("interview.mp4", sample_fps=2.0)
        frames, timestamps = loader.load_frames()
        print(f"Loaded {len(frames)} frames")
    """

    SUPPORTED_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm"})

    def __init__(
        self,
        path: str | Path,
        sample_fps: float = 2.0,
        max_frames: int = 120,
    ) -> None:
        self._path       = Path(path)
        self._sample_fps = max(0.1, sample_fps)
        self._max_frames = max(1, max_frames)
        self._validate()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate(self) -> None:
        if not self._path.exists():
            raise VideoLoadError(f"Video file not found: '{self._path}'")
        if self._path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise VideoLoadError(
                f"Unsupported format '{self._path.suffix}'. "
                f"Accepted: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_metadata(self) -> VideoMetadata:
        """
        Return intrinsic video properties without reading all frames.

        Raises
        ------
        VideoLoadError
            If OpenCV cannot open the file.
        """
        cap = cv2.VideoCapture(str(self._path))
        if not cap.isOpened():
            raise VideoLoadError(f"Cannot open video file: '{self._path}'")
        try:
            fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return VideoMetadata(
                width=width,
                height=height,
                fps=fps,
                total_frames=total,
                duration_seconds=(total / fps) if fps > 0 else 0.0,
            )
        finally:
            cap.release()

    def iter_frames(self) -> Generator[Tuple[np.ndarray, float], None, None]:
        """
        Yield ``(frame_bgr, timestamp_seconds)`` at the configured sample rate.

        Yields
        ------
        frame : np.ndarray
            BGR uint8 image array.
        timestamp_s : float
            Position of the frame inside the video (seconds from start).
        """
        cap = cv2.VideoCapture(str(self._path))
        if not cap.isOpened():
            raise VideoLoadError(f"Cannot open video file: '{self._path}'")

        try:
            video_fps     = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_step    = max(1, int(round(video_fps / self._sample_fps)))
            est_samples   = min(self._max_frames, total_frames // frame_step)

            logger.info(
                "VideoLoader '%s': %.1f fps → sample every %d frames "
                "(target %.1f fps) → ~%d frames",
                self._path.name, video_fps, frame_step,
                self._sample_fps, est_samples,
            )

            frame_idx     = 0
            sampled_count = 0

            while sampled_count < self._max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % frame_step == 0:
                    yield frame, frame_idx / video_fps
                    sampled_count += 1
                frame_idx += 1

        finally:
            cap.release()

    def load_frames(self) -> Tuple[List[np.ndarray], List[float]]:
        """
        Collect all sampled frames into memory.

        Returns
        -------
        frames : List[np.ndarray]
        timestamps : List[float]
            Corresponding timestamps in seconds.
        """
        frames: List[np.ndarray] = []
        timestamps: List[float]  = []
        for frame, ts in self.iter_frames():
            frames.append(frame)
            timestamps.append(ts)
        logger.info(
            "VideoLoader: extracted %d frames from '%s'.",
            len(frames), self._path.name,
        )
        return frames, timestamps
