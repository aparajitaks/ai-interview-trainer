"""
cv_models package
-----------------
Public exports for all computer-vision model modules.
"""

from src.cv_models.face_detection import (
    FaceDetector,
    FaceDetectorLoadError,
    BoundingBox,
)
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
from src.cv_models.posture_detection import (
    PostureDetector,
    PostureDetectorLoadError,
    PostureResult,
)
from src.cv_models.feedback_engine import (
    FeedbackEngine,
    FeedbackSnapshot,
)

__all__ = [
    # V1
    "FaceDetector",
    "FaceDetectorLoadError",
    "BoundingBox",
    # V2 — Emotion
    "EmotionDetector",
    "EmotionDetectorLoadError",
    "EmotionResult",
    # V2 — Eye contact
    "EyeContactDetector",
    "EyeContactDetectorLoadError",
    "EyeContactResult",
    # V2 — Posture
    "PostureDetector",
    "PostureDetectorLoadError",
    "PostureResult",
    # V2 — Feedback
    "FeedbackEngine",
    "FeedbackSnapshot",
]
