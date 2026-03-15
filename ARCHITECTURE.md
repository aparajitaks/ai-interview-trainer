
This document explains the project's architecture and the purpose of each major component. It is intended for engineers onboarding onto the project and for planning extensions.

Top-level modules
------------------
- `preprocessing/` — Video preprocessing utilities.
  - `video_to_frames.py` extracts frames from input videos at a configurable frame rate. Frames are saved to disk for downstream processing.

- `cv_models/` — Computer vision model implementations. These are lightweight, production-friendly wrappers around libraries and heuristics.
  - `face_detector.py` — OpenCV Haarcascade face detection. Exposes `load_face_detector()` and `detect_faces()` utilities and a cached loader.
  - `pose_detector.py` — MediaPipe Pose wrapper. Exposes `load_pose_detector()`, `detect_pose()`, and `get_posture_score()`.
  - `eye_contact.py` — Heuristic eye-contact estimator using OpenCV Haar eye cascade. Provides per-frame scoring and aggregation.
  - `emotion_model.py` — HuggingFace `transformers` image-classification pipeline integration for facial emotion recognition. Includes mapping and aggregation functions.

- `evaluation/` — Metrics, scoring and feedback generation.
  - `metrics.py` — Normalizes raw model outputs to stable [0,1] metrics.
  - `scoring.py` — Weighted aggregation of component metrics into a final score.
  - `feedback_engine.py` — Rule-based feedback generation (text suggestions) based on thresholds.

- `pipelines/` — High-level inference wiring.
  - `inference_pipeline.py` — Orchestrates frame extraction, model runs, metric normalization, scoring and feedback. Returns a structured JSON-like dict.

- `interview_engine/` — Session orchestration and question logic.
  - `question_generator.py` — Simple deterministic question generator.
  - `session_manager.py` — In-memory session storage for questions, answers and feedback.
  - `interview_manager.py` — High-level manager that coordinates questions, session state and calls into the inference pipeline.

- `database/` — Persistence layer using SQLAlchemy + SQLite.
  - `db.py` — DB engine, `SessionLocal` and `Base` declarative base.
  - `models.py` — SQLAlchemy models (User, InterviewSession, AnswerResult).
  - `crud.py` — Synchronous CRUD helpers for saving sessions and answers.

- `api/` — FastAPI application and HTTP routes for starting interviews, submitting answers, finishing sessions and retrieving results.

- `Dockerfile` / `docker-compose.yml` — Containerization configuration for local deployment.

Design principles
------------------
- Modular: each responsibility is encapsulated in a small module with a clear contract.
- Headless-first: all modules are safe to run in non-GUI, CI or server environments.
- Defensive: inputs are validated and scores are clamped to [0,1] to ensure pipeline stability.
- Production-ready primitives: caching helpers, SQLAlchemy-based persistence, and containerization are included.
- No external state assumptions: model downloads happen at runtime and must be provisioned in production.

Operational notes
------------------
- Model artifacts (HF weights, MediaPipe graphs) are not checked into the repo. For reproducible deployments consider pre-populating a model cache volume or baking models into a base image.
- SQLite is suitable for lightweight prototyping and testing. For multi-process production deployments switch to a managed RDBMS and adjust `database/db.py` accordingly.
