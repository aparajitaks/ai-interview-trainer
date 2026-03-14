# Pipeline Description — AI Interview Trainer

This document describes the canonical inference pipeline used by the project.

High-level flow
----------------
video → frames → models → scoring → feedback → api → db

1. Video → Frames (preprocessing)
   - The pipeline begins by extracting frames from a submitted video. This is handled by `preprocessing.video_to_frames`. Frames are stored on disk (under `storage/frames` or a temporary directory) so the downstream modules can operate on still images.

2. Models (cv_models)
   - Face detection (`cv_models.face_detector`): detects faces and returns bounding boxes `(x,y,w,h)`. The first detected face per frame is used as the primary subject for metrics.
   - Pose detection (`cv_models.pose_detector`): uses MediaPipe to extract landmarks; `get_posture_score()` computes a posture quality metric based on shoulder/hip alignment.
   - Eye contact (`cv_models.eye_contact`): heuristically detects eye regions inside the face crop and computes a per-frame eye-contact score; `get_eye_contact_score()` aggregates across frames.
   - Emotion (`cv_models.emotion_model`): uses a HuggingFace `transformers` image-classification pipeline to predict an emotion label and confidence for each face crop. An internal mapping (`EMOTION_SCORE_MAP`) maps common labels to heuristic scores.

3. Scoring (evaluation)
   - Each raw model output is normalized to a [0,1] metric using `evaluation.metrics`.
   - `evaluation.scoring.compute_final_score()` aggregates the normalized metrics using predetermined weights (emotion 0.3, eye 0.3, posture 0.4) to produce a final score in [0,1].

4. Feedback (evaluation.feedback_engine)
   - Rule-based feedback is generated from component metrics. Example rules:
     - eye < 0.5 → "Maintain better eye contact"
     - posture < 0.5 → "Try to sit straight"
     - emotion < 0.5 → "Show more confidence"

5. API
   - The `pipelines.inference_pipeline` returns a structured result which the API returns to callers and persists to the DB.
   - `api/routes/interview.py` orchestrates starting sessions, submitting answers (video paths), and finishing sessions.

6. DB
   - The persistence layer stores sessions and per-answer results in a SQLite database via `database.crud`.

Key implementation notes
-------------------------
- All intermediate scores are clamped to [0,1] to avoid cascading numeric issues.
- The pipeline is designed to be modular and replaceable: for example, the emotion model can be swapped without changing the rest of the pipeline.
- The pipeline favors deterministic, testable heuristics for eye-contact and posture; more advanced models can be integrated later behind the same interface.

Running the pipeline programmatically
-------------------------------------
Call `pipelines.inference_pipeline.run_inference(video_path)` to run the entire flow and obtain a result dict with fields:

```json
{
  "emotion_score": 0.0-1.0,
  "eye_score": 0.0-1.0,
  "posture_score": 0.0-1.0,
  "final_score": 0.0-1.0,
  "feedback": ["...", "..."]
}
```

For API-driven usage, clients POST the video path to `/interview/answer` (or upload files in a future iteration) and receive the recorded session snapshot.
