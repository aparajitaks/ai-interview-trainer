from __future__ import annotations

import logging
from typing import Tuple, Sequence, Dict, Any, Optional

import os
import glob
import cv2
import numpy as np

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Emotion score mapping to convert label -> heuristic score when helpful.
EMOTION_SCORE_MAP = {
    "happy": 1.0,
    "neutral": 0.7,
    "surprise": 0.8,
    "sad": 0.3,
    "angry": 0.2,
    "fear": 0.2,
    "disgust": 0.1,
}

# Module-level cache for the transformers pipeline
_emotion_model = None


def get_emotion_model(model_name: str = "microsoft/resnet-50", device: Optional[int] = None):
    """Return a cached emotion model pipeline, loading it on first call."""
    global _emotion_model
    if _emotion_model is None:
        _emotion_model = load_emotion_model(model_name=model_name, device=device)
    return _emotion_model


def _to_rgb_image(face_img: np.ndarray) -> np.ndarray:
    """Convert a BGR numpy image to RGB numpy image expected by transformers.

    The helper accepts only valid numpy images. Callers should guard None
    inputs and handle exceptions. We intentionally keep the function strict to
    surface invalid input types early.
    """
    if face_img is None:
        raise ValueError("face_img must be a valid numpy array")
    if face_img.dtype != np.uint8:
        face_img = face_img.astype(np.uint8)
    return cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)


def load_emotion_model(model_name: str = "microsoft/resnet-50", device: Optional[int] = None):
    """Load a HuggingFace Transformers image-classification pipeline.

    Args:
        model_name: Model identifier on the HuggingFace Hub. Default is
            'nateraw/fer' which is a commonly used FER (facial emotion
            recognition) checkpoint. Replace as needed.
        device: Device index for PyTorch (-1 for CPU, 0+ for CUDA). If None
            the function will automatically pick GPU if available.

    Returns:
        A Transformers pipeline object ready to run predictions.

    Raises:
        ImportError: if transformers or torch are not available.
    """

    try:
        from transformers import pipeline
        import torch
    except Exception as exc:  # pragma: no cover - environment dependent
        log.exception("transformers or torch not available: %s", exc)
        raise ImportError("transformers and torch are required for emotion model") from exc

    # Auto-select device if not provided
    if device is None:
        device = 0 if torch.cuda.is_available() else -1

    try:
        model = pipeline("image-classification", model=model_name, device=device)
    except Exception as exc:  # pragma: no cover - model download/runtime dependent
        log.exception("Failed to initialize transformers pipeline: %s", exc)
        raise RuntimeError(
            "Failed to load emotion model pipeline. Ensure network access to "
            "download the model or that the model name is correct."
        ) from exc

    log.info("Loaded emotion model pipeline: %s (device=%s)", model_name, device)
    return model


def predict_emotion(face_img: np.ndarray, model) -> Tuple[str, float]:
    """Predict emotion label and confidence for a single face image.

    Args:
        face_img: Face crop in BGR numpy format (as returned by OpenCV).
        model: Transformers image-classification pipeline returned by
            ``load_emotion_model``.

    Returns:
        Tuple of (label, confidence) where confidence is a float in [0,1].
    """

    # Defensive: if face image is missing, return a neutral baseline
    if face_img is None:
        return "neutral", 0.0

    # If caller didn't pass a model, try to use cached loader
    if model is None:
        try:
            model = get_emotion_model()
        except Exception:
            log.exception("Failed to get emotion model; returning neutral")
            return "neutral", 0.0

    try:
        rgb = _to_rgb_image(face_img)
    except Exception:
        log.exception("Invalid face_img passed to predict_emotion")
        return "neutral", 0.0

    # transformers pipelines accept PIL images or numpy arrays in RGB.
    try:
        preds = model(rgb, top_k=1)
    except Exception as exc:
        log.exception("Emotion model inference failed: %s", exc)
        return "error", 0.0

    if not preds:
        return "unknown", 0.0

    top = preds[0]
    label = str(top.get("label", "unknown"))
    score = float(top.get("score", 0.0))

    # Apply heuristic mapping when available, falling back to model score
    label_key = label.lower()
    mapped = EMOTION_SCORE_MAP.get(label_key, score)
    score = float(np.clip(mapped, 0.0, 1.0))
    return label, score


def get_emotion_score(faces: Sequence[np.ndarray], model) -> Dict[str, Any]:
    """Aggregate emotion predictions across multiple face crops.

    The aggregation uses a weighted vote: each predicted label contributes its
    confidence to that label's total. The final label is the one with highest
    total weight and the reported confidence is the mean confidence for that
    label among frames where it was predicted.

    Args:
        faces: Sequence of face crops (BGR numpy images).
        model: Transformers pipeline.

    Returns:
        Dict with keys: label (str), confidence (float 0..1), details (list of per-face predictions).
    """

    if not faces:
        return {"label": "none", "confidence": 0.0, "details": []}

    totals = {}
    counts = {}
    details = []

    for face in faces:
        try:
            label, score = predict_emotion(face, model)
        except Exception:
            label, score = "error", 0.0

        # Ensure score is clamped and use mapping consistency
        score = float(np.clip(score, 0.0, 1.0))
        details.append({"label": label, "score": score})
        totals[label] = totals.get(label, 0.0) + score
        counts[label] = counts.get(label, 0) + 1

    if not totals:
        return {"label": "none", "confidence": 0.0, "details": details}

    # Choose label with max total weight
    best_label = max(totals.items(), key=lambda t: t[1])[0]
    # Mean confidence for this label
    mean_conf = totals[best_label] / counts[best_label]
    mean_conf = float(np.clip(mean_conf, 0.0, 1.0))

    return {"label": best_label, "confidence": float(mean_conf), "details": details}


def test_main(frames_dir: str = "storage/frames", model_name: str = "microsoft/resnet-50") -> None:
    """Headless test: detect first face, run emotion model and write annotated image."""

    try:
        from cv_models.face_detector import load_face_detector, detect_faces
    except Exception:
        log.exception("face_detector import failed")
        raise

    # find a sample frame
    patterns = ["*.jpg", "*.jpeg", "*.png"]
    sample = None
    for p in patterns:
        files = glob.glob(os.path.join(frames_dir, p))
        if files:
            files.sort()
            sample = files[0]
            break

    if sample is None:
        log.error("No frames found in %s. Run preprocessing first.", frames_dir)
        return

    frame = cv2.imread(sample)
    if frame is None:
        log.error("Failed to read sample frame: %s", sample)
        return

    face_detector = load_face_detector()
    faces = detect_faces(frame, face_detector)
    if not faces:
        log.error("No faces detected in sample frame")
        return

    # For test, use first face
    x, y, w, h = faces[0]
    face_crop = frame[y : y + h, x : x + w]

    model = get_emotion_model(model_name=model_name)
    label, confidence = predict_emotion(face_crop, model)
    log.info("Predicted emotion: %s (%.3f)", label, confidence)

    # Annotate and write
    annotated = frame.copy()
    color = (0, 255, 0) if confidence >= 0.5 else (0, 140, 255)
    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
    cv2.putText(annotated, f"{label}:{confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    out_path = os.path.join(frames_dir, "annotated_emotion.jpg")
    cv2.imwrite(out_path, annotated)
    log.info("Wrote annotated emotion image to: %s", out_path)


if __name__ == "__main__":
    test_main()
