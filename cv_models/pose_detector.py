from __future__ import annotations

import logging
import os
import glob
from typing import List, Dict, Optional, Tuple

BBox = Tuple[int, int, int, int]

_pose_detector = None


def get_pose_detector(*, static_image_mode: bool = False, model_complexity: int = 1, enable_segmentation: bool = False):
    """Return a cached MediaPipe Pose detector (loads on first call).

    This wrapper follows the project's caching pattern: it calls
    ``load_pose_detector`` and stores the resulting detector in a
    module-level variable for reuse.
    """
    global _pose_detector
    if _pose_detector is None:
        _pose_detector = load_pose_detector(static_image_mode=static_image_mode, model_complexity=model_complexity, enable_segmentation=enable_segmentation)
    return _pose_detector

import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.framework.formats.landmark_pb2 import NormalizedLandmark
except Exception:  # pragma: no cover - security: allow graceful import failure
    mp = None  # type: ignore

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_pose_detector(static_image_mode: bool = False, model_complexity: int = 1, enable_segmentation: bool = False):
    """Create and return a MediaPipe Pose detector.

    Args:
        static_image_mode: Whether to treat input images as a batch of static
            and possibly unrelated images, or a video stream.
        model_complexity: Model complexity parameter (0,1,2) trading off
            accuracy for latency.
        enable_segmentation: Whether to enable segmentation (not required here).

    Returns:
        An instance of ``mediapipe.solutions.pose.Pose``.

    Raises:
        ImportError: if MediaPipe is not installed.
    """

    if mp is None:
        log.error("mediapipe is not installed. Please install 'mediapipe' to use pose detection.")
        raise ImportError("mediapipe is required for pose detection")

    mp_pose = mp.solutions.pose
    try:
        detector = mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=enable_segmentation,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        log.exception(
            "Failed to initialize MediaPipe Pose detector: %s", exc
        )
        raise RuntimeError(
            "MediaPipe Pose initialization failed. Ensure 'mediapipe' is installed "
            "and compatible with your platform (see https://github.com/google/mediapipe). "
            "If using macOS/arm64, prefer a mediapipe build that includes the binary graphs/models."
        ) from exc

    log.info("Loaded MediaPipe Pose detector (model_complexity=%s)", model_complexity)
    return detector


def detect_pose(frame: np.ndarray, detector) -> List[Dict[str, float]]:
    """Detect pose landmarks in a BGR frame using a MediaPipe Pose detector.

    Args:
        frame: BGR image as numpy array.
        detector: A MediaPipe Pose instance returned by ``load_pose_detector``.

    Returns:
        A list of landmarks where each landmark is a dict with keys
        (index, x, y, z, visibility). Coordinates are normalized [0,1].
    """

    if mp is None:
        raise ImportError("mediapipe is required for detect_pose")

    if frame is None:
        log.warning("Empty frame passed to detect_pose")
        return []

    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = detector.process(image_rgb)

    if not results.pose_landmarks:
        log.debug("No pose landmarks detected")
        return []

    landmarks: List[Dict[str, float]] = []
    for i, lm in enumerate(results.pose_landmarks.landmark):
        landmarks.append({
            "index": i,
            "x": float(lm.x),
            "y": float(lm.y),
            "z": float(lm.z),
            "visibility": float(getattr(lm, "visibility", 0.0)),
        })

    log.debug("Extracted %d landmarks", len(landmarks))
    return landmarks


def draw_pose(frame: np.ndarray, landmarks: List[Dict[str, float]], color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
    """Draw pose landmarks onto the frame and return an annotated copy.

    Args:
        frame: BGR image as numpy array.
        landmarks: List of landmark dicts as returned by ``detect_pose``.
        color: Drawing color for keypoints.

    Returns:
        Annotated BGR image copy.
    """

    if mp is None:
        raise ImportError("mediapipe is required for draw_pose")

    if frame is None:
        raise ValueError("frame must be a valid image array")

    out = frame.copy()

    if not landmarks:
        return out

    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    landmark_list = mp.framework.formats.landmark_pb2.NormalizedLandmarkList()
    for lm in landmarks:
        nl = NormalizedLandmark()
        nl.x = lm["x"]
        nl.y = lm["y"]
        nl.z = lm.get("z", 0.0)
        landmark_list.landmark.append(nl)

    img_rgb = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    mp_drawing.draw_landmarks(img_rgb, landmark_list, mp_pose.POSE_CONNECTIONS)
    out_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    return out_bgr


def get_posture_score(landmarks: List[Dict[str, float]]) -> float:
    """Compute a simple posture score from pose landmarks.

    The score is based on how vertically aligned the torso is. We compute the
    midpoint between shoulders and hips and measure the angle of that vector
    to the vertical. The score ranges from 0.0 (poor) to 1.0 (excellent).

    Args:
        landmarks: List of landmark dicts from ``detect_pose``.

    Returns:
        Float posture score between 0 and 1.
    """

    if not landmarks:
        return 0.0

    idx = {
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_hip": 23,
        "right_hip": 24,
    }

    def lm(i: int) -> Optional[Dict[str, float]]:
        for l in landmarks:
            if l.get("index") == i:
                return l
        return None

    ls = lm(idx["left_shoulder"]) 
    rs = lm(idx["right_shoulder"]) 
    lh = lm(idx["left_hip"]) 
    rh = lm(idx["right_hip"]) 

    if not all([ls, rs, lh, rh]):
        log.debug("Not all torso landmarks present for posture scoring")
        return 0.0

    mid_shoulder = ((ls["x"] + rs["x"]) / 2.0, (ls["y"] + rs["y"]) / 2.0)
    mid_hip = ((lh["x"] + rh["x"]) / 2.0, (lh["y"] + rh["y"]) / 2.0)

    vx = mid_shoulder[0] - mid_hip[0]
    vy = mid_shoulder[1] - mid_hip[1]

    import math

    v_norm = math.hypot(vx, vy)
    if v_norm == 0:
        return 0.0

    dot = (vx * 0.0) + (vy * -1.0)
    cos_theta = max(-1.0, min(1.0, dot / v_norm))
    angle = math.acos(cos_theta)  # radians; 0 means vertical

    score = max(0.0, 1.0 - (angle / (math.pi / 2)))

    vis = [ls.get("visibility", 0.0), rs.get("visibility", 0.0), lh.get("visibility", 0.0), rh.get("visibility", 0.0)]
    visibility = sum(vis) / len(vis)
    final = float(score * visibility)

    final = float(np.clip(final, 0.0, 1.0))
    return final


def _find_first_frame(frames_dir: str = "storage/frames") -> Optional[str]:
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    for p in patterns:
        files = glob.glob(os.path.join(frames_dir, p))
        if files:
            files.sort()
            return files[0]
    return None


def test_main(frames_dir: str = "storage/frames") -> None:
    """Headless test that runs pose detection on a sample frame and writes output."""

    if mp is None:
        log.error("mediapipe not available; skipping pose detector test")
        return

    detector = load_pose_detector()
    sample = _find_first_frame(frames_dir)
    if sample is None:
        log.error("No frames found in %s. Run preprocessing first.", frames_dir)
        return

    log.info("Using sample frame: %s", sample)
    frame = cv2.imread(sample)
    if frame is None:
        log.error("Failed to read image: %s", sample)
        return

    landmarks = detect_pose(frame, detector)
    log.info("Detected %d landmarks", len(landmarks))
    score = get_posture_score(landmarks)
    log.info("Posture score: %.3f", score)

    annotated = draw_pose(frame, landmarks)
    out_path = os.path.join(frames_dir, "annotated_pose.jpg")
    cv2.imwrite(out_path, annotated)
    log.info("Wrote annotated pose image to: %s", out_path)


if __name__ == "__main__":
    test_main()
