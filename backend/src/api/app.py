"""
app.py
------
FastAPI application for the AI Interview Trainer video analysis backend.

The server accepts uploaded interview videos, processes them through the
V2 behaviour analysis pipeline, and returns structured JSON feedback.

Architecture
~~~~~~~~~~~~
* ``lifespan`` loads all ML models **once** at startup and stores the
  pipeline in ``app.state``.  No model is loaded per-request.
* File uploads are written to a temp file, processed, then deleted.
* Environment variables control tunable knobs (SAMPLE_FPS, MAX_FRAMES,
  MAX_VIDEO_SIZE_MB) without changing code.

Endpoints
~~~~~~~~~
  POST /analyze-video — Upload video, receive JSON feedback.
  GET  /health        — Liveness / readiness check.

Run
~~~
    uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload

Endpoints (v2.1)
~~~~~~~~~~~~~~~~
  POST /analyze-video         — Upload video, receive JSON feedback.
  GET  /health                — Liveness / readiness check.
  POST /interview/start       — Start a live AI interview session.
  POST /interview/submit-answer — Submit audio answer, get next question.
  POST /interview/end         — End session, receive final evaluation.
"""

from __future__ import annotations

import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.pipeline.video_pipeline import AnalysisResult, VideoAnalysisPipeline
from src.preprocessing.video_loader import VideoLoadError, VideoLoader
from src.utils.config import AppConfig
from src.utils.logger import get_logger
from src.api.interview      import router as interview_router
from src.api.evaluation     import router as evaluation_router
from src.api.ai_interview   import router as ai_interview_router
from src.api.live_feedback  import router as live_feedback_router
from src.api.code_runner    import router as code_runner_router

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Runtime configuration (override via environment variables)
# ---------------------------------------------------------------------------

MAX_VIDEO_SIZE_MB: int   = int(os.getenv("MAX_VIDEO_SIZE_MB", "100"))
SAMPLE_FPS:        float = float(os.getenv("SAMPLE_FPS", "2.0"))
MAX_FRAMES:        int   = int(os.getenv("MAX_FRAMES", "120"))

# MIME types accepted at the endpoint (content-type sniffing)
_ALLOWED_CONTENT_TYPES = frozenset({
    "video/mp4",
    "video/quicktime",       # .mov
    "video/avi",
    "video/x-msvideo",       # .avi
    "video/x-matroska",      # .mkv
    "video/webm",
    "application/octet-stream",  # some clients don't set a specific type
})

# ---------------------------------------------------------------------------
# Lifespan — load models once, release on shutdown
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    * Startup : instantiate ``VideoAnalysisPipeline`` (loads MediaPipe +
                Haar models into memory).
    * Shutdown: release all model resources cleanly.
    """
    logger.info("API startup: loading ML models …")
    cfg      = AppConfig()
    pipeline = VideoAnalysisPipeline(cfg)
    app.state.pipeline = pipeline
    app.state.config   = cfg
    logger.info("API startup: models loaded — server is ready.")

    yield  # ← server is running here

    logger.info("API shutdown: releasing ML models.")
    pipeline.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title       = "AI Interview Trainer — API",
    description = (
        "AI-powered interview analysis and live interview system.\n\n"
        "- **POST /analyze-video** — Upload a video, receive behaviour feedback\n"
        "- **POST /interview/start** — Start a live AI interview session\n"
        "- **POST /interview/submit-answer** — Submit audio, receive next question\n"
        "- **POST /interview/end** — Get final evaluation\n"
    ),
    version  = "2.1.0",
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)

# Mount routers
app.include_router(interview_router)
app.include_router(evaluation_router)
app.include_router(ai_interview_router)
app.include_router(live_feedback_router)
app.include_router(code_runner_router)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/health",
    summary             = "Liveness / readiness check",
    response_description = "Service status and pipeline readiness",
)
async def health() -> Dict[str, Any]:
    """
    Return the current health of the service.

    ``pipeline_ready`` is ``false`` only during the brief startup window
    before models finish loading.
    """
    ready = (
        hasattr(app.state, "pipeline")
        and app.state.pipeline is not None
    )
    return {
        "status":         "ok" if ready else "starting",
        "pipeline_ready": ready,
        "version":        app.version,
        "sample_fps":     SAMPLE_FPS,
        "max_frames":     MAX_FRAMES,
        "max_upload_mb":  MAX_VIDEO_SIZE_MB,
    }


@app.post(
    "/analyze-video",
    summary              = "Analyse an interview video and return behaviour feedback",
    response_description = "Aggregated per-metric analysis results",
)
async def analyze_video(
    file: UploadFile = File(
        ...,
        description="Interview video file (.mp4, .mov, .avi, .mkv)",
    ),
) -> JSONResponse:
    """
    Upload a video file and receive AI-powered interview behaviour analysis.

    The pipeline:
    1. Samples frames at **{SAMPLE_FPS} fps** (configurable via env).
    2. Detects faces (Haar cascade).
    3. Classifies **emotion** from MediaPipe FaceLandmarker blendshapes.
    4. Scores **eye contact** from iris position relative to eye corners.
    5. Classifies **posture** from shoulder+nose landmark geometry.
    6. Aggregates results across all frames.

    Returns
    -------
    ```json
    {
        "emotion":          "Neutral",
        "eye_contact":      72,
        "posture":          "Good",
        "confidence_score": 78,
        "frames_processed": 24,
        "frames_with_face": 22
    }
    ```
    """
    # ── Content-type guard ────────────────────────────────────────────
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail      = (
                f"Unsupported media type '{file.content_type}'. "
                "Please upload a video file (.mp4, .mov, .avi, .mkv)."
            ),
        )

    # ── Read upload into memory & size-check ─────────────────────────
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)

    if size_mb > MAX_VIDEO_SIZE_MB:
        raise HTTPException(
            status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail      = (
                f"Video too large ({size_mb:.1f} MB). "
                f"Maximum allowed: {MAX_VIDEO_SIZE_MB} MB."
            ),
        )

    logger.info("Received '%s' (%.1f MB)", file.filename, size_mb)

    # ── Write to temp file ────────────────────────────────────────────
    suffix   = Path(file.filename or "upload.mp4").suffix.lower() or ".mp4"
    tmp_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # ── Load sampled frames ───────────────────────────────────────
        t0 = time.perf_counter()

        try:
            loader = VideoLoader(
                tmp_path,
                sample_fps = SAMPLE_FPS,
                max_frames = MAX_FRAMES,
            )
            meta   = loader.get_metadata()
            logger.info(
                "Video: %dx%d  %.1f fps  %.1fs  "
                "(sampling every %.1f s → ~%d frames)",
                meta.width, meta.height,
                meta.fps, meta.duration_seconds,
                1.0 / SAMPLE_FPS,
                min(MAX_FRAMES, int(meta.duration_seconds * SAMPLE_FPS)),
            )
            frames, _ = loader.load_frames()

        except VideoLoadError as exc:
            raise HTTPException(
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail      = str(exc),
            ) from exc

        if not frames:
            raise HTTPException(
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail      = (
                    "No frames could be extracted from the video. "
                    "The file may be corrupt or in an unsupported codec."
                ),
            )

        # ── Run pipeline ──────────────────────────────────────────────
        pipeline: VideoAnalysisPipeline = app.state.pipeline
        result: AnalysisResult = pipeline.process(frames)

        elapsed = time.perf_counter() - t0
        logger.info(
            "Analysis of '%s' completed in %.2f s: %s",
            file.filename, elapsed, result.to_dict(),
        )

        return JSONResponse(content=result.to_dict())

    finally:
        # Always delete the temp file — even if an exception occurred.
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError as exc:
                logger.warning("Could not delete temp file '%s': %s", tmp_path, exc)
