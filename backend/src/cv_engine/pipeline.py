"""
pipeline.py
-----------
Entry point for the AI Interview Trainer V2 behavior-analysis CV pipeline.

Run
~~~
    python -m src.cv_engine.pipeline
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
from src.cv_models.feedback_engine import FeedbackEngine
from src.cv_models.posture_detection import (
    PostureDetector,
    PostureDetectorLoadError,
    PostureResult,
)
from src.preprocessing.video_capture import CameraOpenError, VideoCapture
from src.utils.config import AppConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)


_STUB_EMOTION = EmotionResult(label="N/A", confidence=0.0, is_cached=False)
_STUB_EYE = EyeContactResult(score=0.0, is_contact=False)
_STUB_POSTURE = PostureResult(label="N/A", shoulder_tilt_deg=0.0, vertical_lean_deg=0.0)


def _draw_bounding_boxes(
    frame: np.ndarray,
    boxes: list,
    color: tuple,
    thickness: int,
) -> None:
    for x, y, w, h in boxes:
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, thickness)
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + 22), color, cv2.FILLED)
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)


def _draw_status_text(
    frame: np.ndarray,
    text: str,
    position: tuple,
    color: tuple,
    font_scale: float,
    thickness: int,
) -> None:
    font = cv2.FONT_HERSHEY_DUPLEX
    x, y = position
    cv2.putText(frame, text, (x + 1, y + 1), font, font_scale, (0, 0, 0), thickness)
    cv2.putText(frame, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)


def _draw_face_count(frame: np.ndarray, count: int) -> None:
    h, w = frame.shape[:2]
    label = f"Faces: {count}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.52, 1
    (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
    x = w - tw - 12
    y = th + 10
    cv2.rectangle(frame, (x - 6, y - th - 4), (x + tw + 6, y + 4), (22, 22, 38), cv2.FILLED)
    cv2.putText(frame, label, (x, y), font, scale, (200, 200, 220), thickness, cv2.LINE_AA)


def _draw_version_badge(frame: np.ndarray) -> None:
    h, w = frame.shape[:2]
    label = "V2 Behavior Analysis"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale, thickness = 0.40, 1
    (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
    x = w - tw - 10
    y = h - 8
    cv2.putText(frame, label, (x, y), font, scale, (80, 80, 110), thickness, cv2.LINE_AA)


def run_pipeline(config: AppConfig) -> None:
    cfg_cam = config.camera
    cfg_det = config.face_detection
    cfg_disp = config.display

    quit_key = ord(cfg_disp.quit_key)

    logger.info("Initialising face detector ...")
    face_detector = FaceDetector(cfg_det)

    emotion_detector: Optional[EmotionDetector] = None
    eye_detector: Optional[EyeContactDetector] = None
    posture_detector: Optional[PostureDetector] = None

    try:
        logger.info("Initialising emotion detector ...")
        emotion_detector = EmotionDetector(config.emotion, config.models)
    except EmotionDetectorLoadError as exc:
        logger.warning("Emotion detector unavailable: %s", exc)

    try:
        logger.info("Initialising eye-contact detector ...")
        eye_detector = EyeContactDetector(config.eye_contact, config.models)
    except EyeContactDetectorLoadError as exc:
        logger.warning("Eye-contact detector unavailable: %s", exc)

    try:
        logger.info("Initialising posture detector ...")
        posture_detector = PostureDetector(config.posture, config.models)
    except PostureDetectorLoadError as exc:
        logger.warning("Posture detector unavailable: %s", exc)

    feedback_engine = FeedbackEngine(config.feedback)

    logger.info("Starting V2 pipeline. Press '%s' to quit.", cfg_disp.quit_key)

    frame_id = 0
    try:
        with VideoCapture(cfg_cam) as cap:
            while True:
                ok, frame = cap.read_frame()
                if not ok:
                    logger.error("Frame acquisition failed - terminating pipeline.")
                    break

                frame_id += 1
                boxes = face_detector.detect_faces(frame)
                face_count = len(boxes)
                primary_box = boxes[0] if boxes else None

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

                snapshot = feedback_engine.compile(
                    emotion_result=emo_result,
                    eye_result=eye_result,
                    posture_result=pst_result,
                    face_count=face_count,
                    frame_id=frame_id,
                )
                feedback_engine.render(frame, snapshot)

                if face_count > 0:
                    _draw_bounding_boxes(frame, boxes, cfg_det.bbox_color, cfg_det.bbox_thickness)
                    status_text = f"Face Detected ({face_count})"
                    text_color = cfg_disp.text_color_detected
                else:
                    status_text = "No Face Detected"
                    text_color = cfg_disp.text_color_none

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

                cv2.imshow(cfg_disp.window_name, frame)
                if cv2.waitKey(1) & 0xFF == quit_key:
                    logger.info("Quit key pressed - shutting down.")
                    break
    finally:
        if emotion_detector is not None:
            emotion_detector.close()
        if eye_detector is not None:
            eye_detector.close()
        if posture_detector is not None:
            posture_detector.close()

    cv2.destroyAllWindows()
    logger.info("V2 pipeline terminated cleanly.")


def main() -> int:
    config = AppConfig()
    logger.info(
        "AI Interview Trainer - V2 | camera=%d | window='%s'",
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
