from __future__ import annotations

import logging
import os
import glob
from typing import List, Tuple, Optional, Sequence, Union

import cv2
import numpy as np

# Bounding box alias
BBox = Tuple[int, int, int, int]

# Cache the eye cascade to avoid repeated disk loads in a pipeline
_eye_cascade: Optional[cv2.CascadeClassifier] = None


def get_eye_cascade(path: Optional[str] = None) -> cv2.CascadeClassifier:
    """Return a cached eye cascade classifier (loads on first call)."""
    global _eye_cascade
    if _eye_cascade is None:
        _eye_cascade = _load_eye_cascade(path)
    return _eye_cascade


from cv_models.face_detector import load_face_detector, detect_faces

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _load_eye_cascade(path: Optional[str] = None) -> cv2.CascadeClassifier:
    """Load OpenCV Haarcascade for eyes.

    Uses OpenCV's bundled haarcascade_eye.xml by default.
    """
    if path is None:
        path = os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml")

    if not os.path.exists(path):
        log.error("Eye Haarcascade not found at: %s", path)
        raise FileNotFoundError(path)

    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        raise RuntimeError(f"Failed to load eye cascade from: {path}")
    return cascade


def estimate_eye_contact(frame: np.ndarray, face_box: BBox) -> float:
    """Estimate an eye-contact score for a single face in a frame.

    Heuristic summary:
      - Detect eyes within the face bounding box using Haarcascade.
      - If two eyes are found, compute symmetry and tilt between eye centers.
      - The closer the eyes' midpoint to the face center and the smaller the
        inter-eye tilt, the higher the score.

    Args:
        frame: BGR image.
        face_box: (x, y, w, h) face bounding box in pixel coords.

    Returns:
        float between 0.0 and 1.0 representing estimated eye contact.
    """

    if frame is None:
        log.debug("estimate_eye_contact called with None frame")
        return 0.0

    x, y, w, h = face_box
    # Defensive clamps
    h_img, w_img = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w_img, x + w), min(h_img, y + h)
    if x1 >= x2 or y1 >= y2:
        log.debug("Invalid face box: %s", face_box)
        return 0.0

    face_roi = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

    eye_cascade = get_eye_cascade()
    # detectMultiScale parameters tuned for faces: scale small to find eyes
    eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(10, 10))

    if len(eyes) == 0:
        log.debug("No eyes detected for face box: %s", face_box)
        return 0.0

    # Convert eye coordinates to full-image coordinates and compute centers
    eye_centers: List[Tuple[float, float]] = []
    for (ex, ey, ew, eh) in eyes:
        cx = x1 + ex + ew / 2.0
        cy = y1 + ey + eh / 2.0
        eye_centers.append((cx, cy))

    # If multiple detections, pick two with largest width (likely true eyes)
    if len(eye_centers) > 2:
        # sort by width of detection
        eyes_sorted = sorted(zip(eyes, eye_centers), key=lambda t: t[0][2], reverse=True)
        eye_centers = [c for (_, c) in eyes_sorted[:2]]

    # Compute midpoint and symmetry
    face_cx = x + w / 2.0
    face_cy = y + h / 2.0

    if len(eye_centers) == 1:
        # Single-eye detection: weaker signal. Score based on how close that eye
        # is to the horizontal center of the face.
        ecx, ecy = eye_centers[0]
        horiz_offset = abs(ecx - face_cx) / (w / 2.0)
    score = max(0.0, 1.0 - horiz_offset)
    log.debug("Single eye score=%.3f (offset=%.3f)", score, horiz_offset)
    # Clamp for pipeline safety
    score = float(np.clip(score, 0.0, 1.0))
    return score

    # Two eyes: compute midpoint and tilt
    (x1c, y1c), (x2c, y2c) = eye_centers[0], eye_centers[1]
    mid_x = (x1c + x2c) / 2.0
    mid_y = (y1c + y2c) / 2.0

    horiz_offset = abs(mid_x - face_cx) / (w / 2.0)
    # tilt angle (radians). If head is turned, eyes will not be horizontal
    dy = y2c - y1c
    dx = x2c - x1c if x2c != x1c else 1e-6
    angle = abs(np.arctan2(dy, dx))

    # Normalize metrics to [0,1]
    offset_score = max(0.0, 1.0 - horiz_offset)  # 1 is centered
    max_angle = 0.5  # ~28 degrees; larger tilt reduces score
    angle_score = max(0.0, 1.0 - (angle / max_angle))

    # Distance between eyes relative to face width: too small might indicate oblique view
    eye_dist = np.hypot(dx, dy)
    norm_eye_dist = eye_dist / float(w)  # typical front-facing ~0.25-0.35
    dist_score = 1.0 if 0.15 <= norm_eye_dist <= 0.45 else max(0.0, 1.0 - abs(0.3 - norm_eye_dist) * 2)

    # Combine scores multiplicatively to penalize any strong deviation
    score = offset_score * angle_score * dist_score
    score = float(max(0.0, min(1.0, score)))
    # Final clamp to ensure score is in [0,1]
    score = float(np.clip(score, 0.0, 1.0))
    log.debug("eye_centers=%s offset_score=%.3f angle_score=%.3f dist_score=%.3f => score=%.3f",
              eye_centers, offset_score, angle_score, dist_score, score)

    return score


def get_eye_contact_score(frames_or_pairs: Sequence[Union[np.ndarray, Tuple[np.ndarray, BBox]]], max_frames: int = 30) -> float:
    """Aggregate eye-contact score over multiple frames.

    Accepts either a list of frames (will auto-detect faces using the face
    detector) or a list of (frame, face_box) pairs.

    Args:
        frames_or_pairs: sequence of frames or (frame, face_box) tuples.
        max_frames: limit how many frames to process for speed.

    Returns:
        Average eye contact score across processed frames (0..1). If no valid
        frames or faces found, returns 0.0.
    """

    # Prepare face detector for automatic face detection if needed
    # Prefer the cached face detector helper to avoid repeated loads
    try:
        from cv_models.face_detector import get_face_detector
        face_detector = get_face_detector()
    except Exception:
        # Fallback to direct loader if helper is not available
        face_detector = load_face_detector()

    scores: List[float] = []
    count = 0

    for item in frames_or_pairs:
        if count >= max_frames:
            break

        if isinstance(item, tuple):
            frame, face_box = item
        else:
            frame = item
            if frame is None:
                log.debug("Skipping None frame in get_eye_contact_score")
                continue
            # auto-detect faces and take first
            faces = detect_faces(frame, face_detector)
            if not faces:
                log.debug("No face detected for auto frame; skipping")
                continue
            face_box = faces[0]

        score = estimate_eye_contact(frame, face_box)
        scores.append(score)
        count += 1

    if not scores:
        return 0.0

    avg = float(sum(scores) / len(scores))
    # Clamp aggregated score
    avg = float(np.clip(avg, 0.0, 1.0))
    log.info("Computed eye-contact score over %d frames: %.3f", len(scores), avg)
    return avg


def _find_first_frame(frames_dir: str = "storage/frames") -> Optional[str]:
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    for p in patterns:
        files = glob.glob(os.path.join(frames_dir, p))
        if files:
            files.sort()
            return files[0]
    return None


def test_main(frames_dir: str = "storage/frames") -> None:
    """Headless test: run eye-contact estimation on a sample frame and write annotated output."""

    sample = _find_first_frame(frames_dir)
    if sample is None:
        log.error("No frames found in %s. Run preprocessing first.", frames_dir)
        return

    frame = cv2.imread(sample)
    if frame is None:
        log.error("Failed to read sample frame: %s", sample)
        return

    # auto-detect face
    try:
        from cv_models.face_detector import get_face_detector
        face_detector = get_face_detector()
    except Exception:
        face_detector = load_face_detector()
    faces = detect_faces(frame, face_detector)
    if not faces:
        log.error("No faces detected in sample frame")
        return

    box = faces[0]
    score = estimate_eye_contact(frame, box)
    log.info("Eye-contact score for %s: %.3f", sample, score)

    # Annotate and write
    x, y, w, h = box
    annotated = frame.copy()
    color = (0, 255, 0) if score >= 0.5 else (0, 140, 255)
    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
    cv2.putText(annotated, f"eye_contact={score:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    out_path = os.path.join(frames_dir, "annotated_eye_contact.jpg")
    cv2.imwrite(out_path, annotated)
    log.info("Wrote annotated eye contact image to: %s", out_path)


if __name__ == "__main__":
    test_main()
