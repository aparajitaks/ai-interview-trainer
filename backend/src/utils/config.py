"""
config.py
---------
Centralised runtime configuration for the AI Interview Trainer.

All tuneable parameters are declared here as typed, frozen dataclass
fields so that downstream modules can import immutable settings without
spreading magic numbers across the codebase.

Usage
-----
    from src.utils.config import AppConfig

    cfg = AppConfig()
    cap = cv2.VideoCapture(cfg.camera.index)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple

# Project root — two levels up from this file (src/utils/config.py → project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Sub-configurations  (group related knobs into their own dataclass)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CameraConfig:
    """Webcam / video-source settings."""

    index: int = 0
    """Camera device index passed to ``cv2.VideoCapture``."""

    frame_width: int = 1280
    """Requested capture width in pixels (may be capped by hardware)."""

    frame_height: int = 720
    """Requested capture height in pixels (may be capped by hardware)."""

    fps: int = 30
    """Requested frames per second (may be capped by hardware)."""


@dataclass(frozen=True)
class FaceDetectionConfig:
    """Haar Cascade face detector settings."""

    scale_factor: float = 1.1
    """
    Specifies how much the image size is reduced at each image scale.
    Smaller values increase recall at the cost of speed.
    """

    min_neighbors: int = 5
    """
    Specifies how many neighbors each candidate rectangle should retain.
    Higher values reduce false positives.
    """

    min_size: Tuple[int, int] = (80, 80)
    """Minimum possible face object size. Smaller sizes are ignored."""

    bbox_color: Tuple[int, int, int] = (0, 220, 100)
    """BGR colour for the bounding-box rectangle drawn on detected faces."""

    bbox_thickness: int = 2
    """Pixel thickness of the drawn bounding-box."""


@dataclass(frozen=True)
class EmotionConfig:
    """FER emotion detector settings."""

    inference_interval: int = 5
    """
    Run emotion inference once every N frames; return the cached result
    on skipped frames. Keeps the pipeline near 30 fps.
    """

    confidence_threshold: float = 0.35
    """
    Minimum FER confidence required to update the cached result.
    Results below this threshold keep the previous cached label.
    """

    use_mtcnn: bool = False
    """
    Whether FER uses MTCNN for its internal face detection step.
    ``False`` uses the faster OpenCV Haar-based detector.
    Since we pass a pre-cropped face ROI, MTCNN is not needed.
    """


@dataclass(frozen=True)
class EyeContactConfig:
    """MediaPipe FaceMesh iris-based eye contact settings."""

    smoothing_window: int = 12
    """
    Number of frames over which the raw iris-deviation score is averaged.
    Larger values dampen flicker but increase lag.
    """

    iris_deviation_threshold: float = 0.28
    """
    Normalised eye-width fraction at which the score reaches 0.0.
    Smaller values make the detector stricter (less tolerance for deviation).
    """

    contact_threshold: float = 0.50
    """
    Smoothed score at or above which ``is_contact`` is set to ``True``.
    """

    min_detection_confidence: float = 0.5
    """MediaPipe FaceMesh minimum detection confidence."""

    min_tracking_confidence: float = 0.5
    """MediaPipe FaceMesh minimum tracking confidence."""


@dataclass(frozen=True)
class PostureConfig:
    """MediaPipe Pose posture analysis settings."""

    model_complexity: int = 0
    """
    MediaPipe Pose model complexity.
    0 = LITE (fastest), 1 = FULL, 2 = HEAVY.
    """

    shoulder_tilt_threshold_deg: float = 15.0
    """
    Shoulder line tilt (degrees from horizontal) above which posture is
    classified as "Leaning".
    """

    slouch_angle_threshold_deg: float = 22.0
    """
    Nose-to-shoulder-midpoint vector deviation from vertical (degrees)
    above which posture is classified as "Slouching".
    """

    min_detection_confidence: float = 0.5
    """MediaPipe Pose minimum detection confidence."""

    min_tracking_confidence: float = 0.5
    """MediaPipe Pose minimum tracking confidence."""


@dataclass(frozen=True)
class FeedbackConfig:
    """Feedback HUD overlay panel settings."""

    panel_x: int = 10
    """Left edge of the HUD panel in pixels from the frame left."""

    panel_y: int = 10
    """Top edge of the HUD panel in pixels from the frame top."""

    panel_width: int = 290
    """Width of the HUD panel in pixels."""

    panel_alpha: float = 0.72
    """Opacity of the HUD panel background (0.0 = transparent, 1.0 = opaque)."""

    line_height: int = 30
    """Pixel height allocated per metric row inside the panel."""


@dataclass(frozen=True)
class DisplayConfig:
    """On-screen overlay / UI settings."""

    window_name: str = "AI Interview Trainer — V2 Behavior Analysis"
    """Title of the OpenCV display window."""

    font_scale: float = 0.7
    """Scale factor for overlay text rendered via ``cv2.putText``."""

    font_thickness: int = 2
    """Thickness of overlay text."""

    text_color_detected: Tuple[int, int, int] = (80, 220, 80)
    """BGR colour for face-detected status text."""

    text_color_none: Tuple[int, int, int] = (60, 60, 220)
    """BGR colour for no-face status text."""

    text_position: Tuple[int, int] = (20, 40)
    """(x, y) pixel coordinates for the top-left corner of face-status text."""

    quit_key: str = "q"
    """Keyboard character that triggers a clean application exit."""


@dataclass(frozen=True)
class ModelConfig:
    """Paths to MediaPipe Tasks API model bundle files."""

    face_landmarker_path: Path = _PROJECT_ROOT / "models" / "face_landmarker.task"
    """
    MediaPipe FaceLandmarker model (float16).
    Used by both the emotion detector (blendshapes) and the eye-contact
    detector (iris landmarks).  Download once with:

        curl -L https://storage.googleapis.com/mediapipe-models/face_landmarker/\
face_landmarker/float16/latest/face_landmarker.task -o models/face_landmarker.task
    """

    pose_landmarker_path: Path = _PROJECT_ROOT / "models" / "pose_landmarker_lite.task"
    """
    MediaPipe PoseLandmarker LITE model (float16).
    Used by the posture detector.  Download once with:

        curl -L https://storage.googleapis.com/mediapipe-models/pose_landmarker/\
pose_landmarker_lite/float16/latest/pose_landmarker_lite.task -o models/pose_landmarker_lite.task
    """


@dataclass(frozen=True)
class AppConfig:
    """
    Root configuration object that composes all sub-configurations.

    Instantiate once at application startup and pass the relevant
    sub-config to each subsystem::

        cfg = AppConfig()
        detector = FaceDetector(cfg.face_detection)
        capture  = VideoCapture(cfg.camera)
    """

    camera: CameraConfig = field(default_factory=CameraConfig)
    face_detection: FaceDetectionConfig = field(default_factory=FaceDetectionConfig)
    emotion: EmotionConfig = field(default_factory=EmotionConfig)
    eye_contact: EyeContactConfig = field(default_factory=EyeContactConfig)
    posture: PostureConfig = field(default_factory=PostureConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    models: ModelConfig = field(default_factory=ModelConfig)
