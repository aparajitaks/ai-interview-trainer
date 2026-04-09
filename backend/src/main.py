"""
main.py
-------
Entry point for the AI Interview Trainer — V2: Behavior Analysis.

Pipeline
~~~~~~~~
    VideoCapture
        → FaceDetector          (Haar Cascade, every frame)
        → EmotionDetector       (FER mini-XCEPTION, every N frames)
        → EyeContactDetector    (MediaPipe FaceMesh iris, every frame)
        → PostureDetector       (MediaPipe Pose LITE, every frame)
        → FeedbackEngine        (compile + render HUD)
        → cv2.imshow

Key design decisions
~~~~~~~~~~~~~~~~~~~~
* All heavyweight objects (models, MediaPipe graphs) are constructed exactly
  once, outside the pipeline loop, to avoid per-frame initialisation cost.
* ``AppConfig`` is the single source of truth; every subsystem receives only
  the config slice it needs.
* Graceful shutdown is guaranteed via the ``VideoCapture`` context manager
  and explicit ``cv2.destroyAllWindows()``.
* Each V2 detector has a corresponding ``*LoadError``; startup errors are
  caught, logged at CRITICAL, and surfaced as non-zero exit codes for CI use.
* On platforms where a V2 dependency is unavailable (e.g. Python version
  incompatibility), the corresponding detector raises its ``*LoadError`` at
  construction time — caught here, logged, and skipped with a stub result.

Run
~~~
    python -m src.main
"""

from __future__ import annotations

import sys
from typing import Optional

import cv2
import numpy as np

from src.cv_models.emotion_detection import (
    EmotionDetector,
    EmotionDetectorLoadError,
    EmotionResult,
)
from src.cv_models.eye_contact import (
    EyeContactDetector,
    EyeContactDetectorLoadError,
    EyeContactResult,
)
from src.cv_models.face_detection import FaceDetector, FaceDetectorLoadError
from src.cv_models.feedback_engine import FeedbackEngine, FeedbackSnapshot
from src.cv_models.posture_detection import (
    PostureDetector,
    PostureDetectorLoadError,
    PostureResult,
)
from src.preprocessing.video_capture import CameraOpenError, VideoCapture
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Stub results (used when a V2 detector failed to load)
# ---------------------------------------------------------------------------

_STUB_EMOTION  = EmotionResult(label="N/A", confidence=0.0, is_cached=False)
_STUB_EYE      = EyeContactResult(score=0.0, is_contact=False)
_STUB_POSTURE  = PostureResult(label="N/A", shoulder_tilt_deg=0.0, vertical_lean_deg=0.0)


# ---------------------------------------------------------------------------
# Overlay helpers  (preserved from V1, colour-scheme updated for V2)
# ---------------------------------------------------------------------------


def _draw_bounding_boxes(
    frame:     np.ndarray,
    boxes:     list,
    color:     tuple,
    thickness: int,
) -> None:
    """
    Draw filled + outlined bounding rectangles for each detected face.

    Mutates ``frame`` in-place to avoid an extra allocation per frame.

    Parameters
    ----------
    frame:     BGR uint8 frame to annotate.
    boxes:     List of ``(x, y, w, h)`` tuples from :meth:`FaceDetector.detect_faces`.
    color:     BGR tuple for the rectangle stroke.
    thickness: Stroke thickness in pixels.
    """
    for x, y, w, h in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        # Subtle filled header strip for better visibility
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + 22), color, cv2.FILLED)
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)


def _draw_status_text(
    frame:      np.ndarray,
    text:       str,
    position:   tuple,
    color:      tuple,
    font_scale: float,
    thickness:  int,
) -> None:
    """
    Render anti-aliased status text with a drop-shadow for readability.

    Parameters
    ----------
    frame:      BGR uint8 frame to annotate.
    text:       Message string to render.
    position:   ``(x, y)`` pixel origin of the text baseline.
    color:      BGR colour of the main text.
    font_scale: OpenCV font scale factor.
    thickness:  Text stroke thickness.
    """
    font = cv2.FONT_HERSHEY_DUPLEX
    x, y = position
    cv2.putText(frame, text, (x + 1, y + 1), font, font_scale, (0, 0, 0), thickness)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)


def _draw_face_count(frame: np.ndarray, count: int) -> None:
    """
    Render a small face-count badge in the top-right corner of the frame.

    Parameters
    ----------
    frame: BGR uint8 frame to annotate.
    count: Number of detected faces.
    """
    h, w = frame.shape[:2]
    label = f"Faces: {count}"
    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.52, 1
    (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
    x = w - tw - 12
    y = th + 10
    cv2.rectangle(frame, (x - 6, y - th - 4), (x + tw + 6, y + 4), (22, 22, 38), cv2.FILLED)
    cv2.putText(frame, label, (x, y), font, scale, (200, 200, 220), thickness, cv2.LINE_AA)


def _draw_version_badge(frame: np.ndarray) -> None:
    """Render a small 'V2' version tag in the bottom-right corner."""
    h, w = frame.shape[:2]
    label = "V2 Behavior Analysis"
    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.40, 1
    (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
    x = w - tw - 10
    y = h - 8
    cv2.putText(frame, label, (x, y), font, scale, (80, 80, 110), thickness, cv2.LINE_AA)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def run_pipeline(config: AppConfig) -> None:
    """
    Execute the V2 real-time behavior-analysis pipeline until the user quits.

    Pipeline steps per frame
    -------------------------
    1. Capture a raw BGR frame from the webcam.
    2. Detect faces (Haar Cascade) → bounding boxes.
    3. Detect emotion (FER CNN, throttled) → label + confidence.
    4. Detect eye contact (MediaPipe FaceMesh iris) → score + boolean.
    5. Detect posture (MediaPipe Pose LITE) → label + angles.
    6. Compile a ``FeedbackSnapshot`` and render the HUD panel.
    7. Annotate the frame with face boxes and status text.
    8. Display the annotated frame; poll for quit key.

    Parameters
    ----------
    config : AppConfig
        Root configuration that parameterises every subsystem.

    Raises
    ------
    CameraOpenError
        Re-raised if the webcam cannot be opened.
    FaceDetectorLoadError
        Re-raised if the Haar Cascade XML is missing / corrupt.
    """
    cfg_cam  = config.camera
    cfg_det  = config.face_detection
    cfg_disp = config.display

    quit_key = ord(cfg_disp.quit_key)

    # ── Initialise detectors (once, before the loop) ──────────────────
    logger.info("Initialising face detector …")
    face_detector = FaceDetector(cfg_det)

    # V2 detectors: each may raise a *LoadError if the dependency is absent.
    emotion_detector:  Optional[EmotionDetector]  = None
    eye_detector:      Optional[EyeContactDetector] = None
    posture_detector:  Optional[PostureDetector]   = None

    try:
        logger.info("Initialising emotion detector (FaceLandmarker blendshapes) …")
        emotion_detector = EmotionDetector(config.emotion, config.models)
    except EmotionDetectorLoadError as exc:
        logger.warning("Emotion detector unavailable: %s", exc)

    try:
        logger.info("Initialising eye-contact detector (FaceLandmarker iris) …")
        eye_detector = EyeContactDetector(config.eye_contact, config.models)
    except EyeContactDetectorLoadError as exc:
        logger.warning("Eye-contact detector unavailable: %s", exc)

    try:
        logger.info("Initialising posture detector (PoseLandmarker LITE) …")
        posture_detector = PostureDetector(config.posture, config.models)
    except PostureDetectorLoadError as exc:
        logger.warning("Posture detector unavailable: %s", exc)

    feedback_engine = FeedbackEngine(config.feedback)

    logger.info(
        "Starting V2 pipeline. Press '%s' to quit.",
        cfg_disp.quit_key,
    )

    frame_id = 0

    try:
        with VideoCapture(cfg_cam) as cap:
            while True:
                ok, frame = cap.read_frame()
                if not ok:
                    logger.error("Frame acquisition failed — terminating pipeline.")
                    break

                frame_id += 1

                # ── Face detection ─────────────────────────────────────
                boxes      = face_detector.detect_faces(frame)
                face_count = len(boxes)
                primary_box = boxes[0] if boxes else None

                # ── Behavior analysis ──────────────────────────────────
                emo_result = (
                    emotion_detector.detect_emotion(frame, primary_box)
                    if emotion_detector is not None
                    else _STUB_EMOTION
                )

                eye_result = (
                    eye_detector.detect_eye_contact(frame)
                    if eye_detector is not None
                    else _STUB_EYE
                )

                pst_result = (
                    posture_detector.detect_posture(frame)
                    if posture_detector is not None
                    else _STUB_POSTURE
                )

                # ── Compile + render HUD ───────────────────────────────
                snapshot = feedback_engine.compile(
                    emotion_result  = emo_result,
                    eye_result      = eye_result,
                    posture_result  = pst_result,
                    face_count      = face_count,
                    frame_id        = frame_id,
                )
                feedback_engine.render(frame, snapshot)

                # ── Face bounding boxes ────────────────────────────────
                if face_count > 0:
                    _draw_bounding_boxes(
                        frame, boxes, cfg_det.bbox_color, cfg_det.bbox_thickness
                    )
                    status_text = f"Face Detected ({face_count})"
                    text_color  = cfg_disp.text_color_detected
                else:
                    status_text = "No Face Detected"
                    text_color  = cfg_disp.text_color_none

                _draw_status_text(
                    frame,
                    status_text,
                    cfg_disp.text_position,
                    text_color,
                    cfg_disp.font_scale,
                    cfg_disp.font_thickness,
                )
                _draw_face_count(frame, face_count)
                _draw_version_badge(frame)

                # ── Display ────────────────────────────────────────────
                cv2.imshow(cfg_disp.window_name, frame)

                if cv2.waitKey(1) & 0xFF == quit_key:
                    logger.info("Quit key pressed — shutting down.")
                    break

    finally:
        # Always release MediaPipe resources, even on unexpected exit.
        if emotion_detector is not None:
            emotion_detector.close()
        if eye_detector is not None:
            eye_detector.close()
        if posture_detector is not None:
            posture_detector.close()

    cv2.destroyAllWindows()
    logger.info("V2 pipeline terminated cleanly.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    """
    Bootstrap the V2 application, run the pipeline, and return an exit code.

    Returns
    -------
    int
        ``0`` on clean exit, ``1`` on a recoverable startup error.
    """
    config = AppConfig()
    logger.info(
        "AI Interview Trainer — V2 | camera=%d | window='%s'",
        config.camera.index,
        config.display.window_name,
    )

    try:
        run_pipeline(config)
    except CameraOpenError as exc:
        logger.critical("Camera error: %s", exc)
        return 1
    except FaceDetectorLoadError as exc:
        logger.critical("Face detector load error: %s", exc)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user (Ctrl-C).")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in pipeline: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
