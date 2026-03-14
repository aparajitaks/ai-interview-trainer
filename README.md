# AI Interview Trainer

AI Interview Trainer is a modular toolkit for recording, analyzing and evaluating video interview answers. It provides a headless pipeline to extract frames from candidate videos, run lightweight computer-vision models (face, pose, eye-contact, emotion), compute normalized metrics, produce an aggregate score and user-facing feedback, and persist results to a local SQLite database. A small FastAPI backend exposes endpoints to orchestrate interview sessions.

This repository is intended for engineering teams building automated interview coaching tools and prototypes.

Features
---------
- Frame extraction from video (preprocessing)
- Face detection (OpenCV Haarcascade)
- Pose estimation (MediaPipe)
- Eye-contact estimation (OpenCV heuristics)
- Emotion recognition (HuggingFace Transformers pipeline)
- Metric normalization and weighted scoring
- Feedback generation rules
- Inference pipeline to compute end-to-end results
- In-memory interview manager and a SQLite-backed persistence layer
- FastAPI HTTP endpoints for session orchestration
- Docker and docker-compose configuration for local deployment

Tech stack
----------
- Python 3.10
- OpenCV for image I/O and Haarcascade detectors
- MediaPipe for pose estimation (optional depending on platform)
- PyTorch + Transformers for emotion recognition (HuggingFace pipeline)
- SQLAlchemy + SQLite for lightweight persistence
- FastAPI + Uvicorn for HTTP API
- Docker / docker-compose for containerized runs

Repository layout (top-level)
-----------------------------
- `api/` — FastAPI app and route definitions
- `cv_models/` — Computer vision modules (face_detector, pose_detector, eye_contact, emotion_model)
- `preprocessing/` — Video → frames extraction utilities
- `pipelines/` — End-to-end inference pipeline wiring
- `evaluation/` — Metric normalization, scoring and feedback generation
- `interview_engine/` — Session orchestration and question generator
- `database/` — SQLAlchemy models, DB setup and CRUD helpers
- `storage/` — Mounted storage for frames, audio and SQLite DB file (created at runtime)
- `Dockerfile`, `docker-compose.yml` — Containerization artifacts

Run locally (recommended development flow)
----------------------------------------
1. Create and activate a virtual environment (zsh/Bash):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

3. Initialize the SQLite database (creates `storage/ai_interview.db`):

```bash
python -c "from database.db import init_db; init_db()"
```

4. Run the FastAPI application:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Environment variables
---------------------
The application supports additional environment variables to tune behavior:

- AIIT_DB_PATH — path to SQLite DB file (default: ./storage/ai_interview.db)
- AIIT_STORAGE_DIR — where uploaded videos are stored (default: ./storage/video)
- AIIT_FRAME_DIR — frames extraction directory (default: ./storage/frames)
- AIIT_LOG_LEVEL — logging level (INFO, DEBUG)
- AIIT_INFERENCE_TIMEOUT — inference timeout in seconds (used by async wrapper)
- AIIT_PRELOAD_MODELS — if true, preload models at startup (true/false)
- AIIT_ROLE — role used by scoring logic (candidate, interviewer, etc.)
- AIIT_ROLE_WEIGHT — optional role multiplier (float)
- AIIT_SAMPLE_FRAMES — number of frames sampled from a video for scoring (default: 5)

Running tests
-------------
Install pytest and run tests:

```bash
pip install pytest
pytest -q
```

MediaPipe note
--------------
MediaPipe can be platform-sensitive (especially on macOS/arm64). If the
pose detector fails to initialize, the API will still start but posture
scoring will be disabled and the model status will report `failed` for
`pose`. For reliable production runs prefer a compatible mediapipe wheel
or run inside a Linux container where MediaPipe binary assets are known to
work.

Run with Docker
---------------
This project includes a Dockerfile and docker-compose configuration for local containerized runs.

1. Build and start using docker-compose:

```bash
docker-compose up --build
```

2. The API will be available at http://localhost:8000. The SQLite database file will be created as `./storage/ai_interview.db` on the host because the compose file mounts `./storage` into the container.

Build and run with Docker (no compose)
------------------------------------

If you don't want to use docker-compose you can build and run the image directly. The examples below mount the host `./storage` into the container so the SQLite DB and uploaded videos persist outside the image.

```bash
# build the image (run from project root)
docker build -t ai-interview-trainer:latest .

# run the container, mounting storage and exposing port 8000
docker run --rm -p 8000:8000 \
  -v "$PWD/storage":/app/storage \
  -e AIIT_PRELOAD_MODELS=false \
  ai-interview-trainer:latest
```

After the container starts the API will be reachable at http://localhost:8000 and the DB will be persisted in `./storage/ai_interview.db` on the host.

API endpoints (HTTP)
--------------------
- POST /interview/start
  - Starts a new interview session. Returns `session_id` and first question.

- POST /interview/answer
  - Body: JSON {"session_id": "<id>", "video_path": "<path_on_server>"}
  - Processes the provided video path via the inference pipeline and records the answer. The pipeline expects the server to be able to read the given video path. (File upload support can be added later.)

- POST /interview/finish
  - Body: JSON {"session_id": "<id>"}
  - Ends the interview and returns a summary and stored DB representation.

- GET /results/session/{session_id}
  - Returns persisted answers and metadata for the given session.

Notes and operational considerations
-----------------------------------
- Models: The emotion model uses HuggingFace transformers and may download model weights on first run. Ensure the runtime has network access or pre-download weights into a mounted cache.
- MediaPipe: On some platforms (macOS/ARM) MediaPipe may require specific wheel builds including native graph assets; see the module logs if initialization fails.
- Storage: The repository mounts `./storage` into the container; large artifacts or model caches should be stored outside the image.

Contributing
------------
Contributions are welcome. For changes touching model behavior, prefer adding unit tests and small datasets for deterministic CI. Follow standard git workflows and open a PR against `main`.

License
-------
Check repository root for license details (not included by default in this scaffold).
AI Interview Trainer Platform

Version 1 — Base ML Pipeline

This project builds an AI system that analyzes interview videos using:

- Computer Vision
- Speech Processing
- NLP
- ML pipeline
- FastAPI backend (later)
- Role-based interview engine (later)

Build order follows real ML engineering workflow.