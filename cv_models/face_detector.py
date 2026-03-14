from __future__ import annotations

import logging
import os
import glob
from typing import List, Tuple, Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_face_detector(path: Optional[str] = None) -> cv2.CascadeClassifier:
    """Load an OpenCV Haarcascade face detector.

    Args:
        path: Optional path to a Haarcascade XML file. If not provided, the
            function will use OpenCV's bundled `haarcascade_frontalface_default.xml`.

    Returns:
        An instance of ``cv2.CascadeClassifier``.
    """

    if path is None:
        # Use OpenCV's bundled haarcascade. This avoids shipping large model
        # files and works across platforms where OpenCV is installed.
        path = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")

    if not os.path.exists(path):
        log.error("Haarcascade file not found: %s", path)
        raise FileNotFoundError(f"Haarcascade file not found: {path}")

    detector = cv2.CascadeClassifier(path)
    if detector.empty():
        log.error("Failed to load Haarcascade classifier from: %s", path)
        raise RuntimeError(f"Failed to load Haarcascade classifier from: {path}")

    log.info("Loaded Haarcascade face detector from: %s", path)
    return detector


def detect_faces(
    frame: np.ndarray,
    detector: cv2.CascadeClassifier,
    scaleFactor: float = 1.1,
    minNeighbors: int = 5,
    minSize: Tuple[int, int] = (30, 30),
) -> List[Tuple[int, int, int, int]]:
    """Detect faces in an image frame.

    Args:
        frame: BGR image as returned by ``cv2.imread`` or a video frame.
        detector: A loaded ``cv2.CascadeClassifier`` instance.
        scaleFactor: Parameter specifying how much the image size is reduced
            at each image scale (see OpenCV docs).
        minNeighbors: Parameter specifying how many neighbors each candidate
            rectangle should have to retain it.
        minSize: Minimum possible object size. Objects smaller than that are ignored.

    Returns:
        A list of bounding boxes in (x, y, w, h) format.
    """

    if frame is None:
        log.warning("Empty frame passed to detect_faces")
        return []

    # Convert to grayscale for the Haarcascade detector which expects gray images
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    rects = detector.detectMultiScale(
        gray, scaleFactor=scaleFactor, minNeighbors=minNeighbors, minSize=minSize
    )

    # Ensure we always return a list of tuples for consistency
    boxes: List[Tuple[int, int, int, int]] = []
    if rects is None:
        return boxes

    # OpenCV may return a numpy array of shape (N,4)
    for r in rects:
        x, y, w, h = int(r[0]), int(r[1]), int(r[2]), int(r[3])
        boxes.append((x, y, w, h))

    log.debug("Detected %d faces", len(boxes))
    return boxes


def draw_faces(
    frame: np.ndarray,
    boxes: List[Tuple[int, int, int, int]],
    color: Tuple[int, int, int] = (0, 255, 0),
    thickness: int = 2,
) -> np.ndarray:
    """Draw bounding boxes on a copy of the frame.

    Args:
        frame: Source BGR image.
        boxes: List of (x, y, w, h) bounding boxes.
        color: Rectangle color (B, G, R).
        thickness: Rectangle thickness.

    Returns:
        Annotated image (a copy of the input frame).
    """

    if frame is None:
        raise ValueError("frame must be a valid image array")

    out = frame.copy()

    for (x, y, w, h) in boxes:
        top_left = (x, y)
        bottom_right = (x + w, y + h)
        cv2.rectangle(out, top_left, bottom_right, color, thickness)

    return out


def _find_first_frame_dir(frames_dir: str = "storage/frames") -> Optional[str]:
    """Helper to find a sample frame under the frames directory.

    Returns path to first image file found or None.
    """

    patterns = ["*.jpg", "*.jpeg", "*.png"]
    for pattern in patterns:
        files = glob.glob(os.path.join(frames_dir, pattern))
        if files:
            files.sort()
            return files[0]
    return None


def test_main(frames_dir: str = "storage/frames") -> None:
    """Test function that runs the detector on a sample frame and writes output.

    The function is safe to run in headless environments: it writes an annotated
    image to the same frames directory and prints detected boxes.
    """

    detector = load_face_detector()

    sample = _find_first_frame_dir(frames_dir)
    if sample is None:
        log.error("No frames found in %s. Run preprocessing first.", frames_dir)
        return

    log.info("Using sample frame: %s", sample)
    frame = cv2.imread(sample)
    if frame is None:
        log.error("Failed to read image: %s", sample)
        return

    boxes = detect_faces(frame, detector)
    log.info("Detected boxes: %s", boxes)

    annotated = draw_faces(frame, boxes)
    out_path = os.path.join(frames_dir, "annotated_faces.jpg")
    cv2.imwrite(out_path, annotated)
    log.info("Wrote annotated output to: %s", out_path)


if __name__ == "__main__":
    # Allow running the module directly for a quick smoke test
    test_main()
