"""FastAPI application for AI Interview Trainer.

Includes interview and results routers. This module creates an app and
initializes shared components used by routes.
"""

from __future__ import annotations

import logging
from config.settings import LOG_LEVEL, DB_PATH, STORAGE_DIR, EMOTION_MODEL
from utils.logger import get_logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import interview as interview_router
from api.routes import results as results_router
from api.routes import health as health_router
import os

log = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Interview Trainer API")

    # Allow frontend dev server origins for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(interview_router.router, prefix="/interview", tags=["interview"])
    app.include_router(results_router.router, prefix="/results", tags=["results"])
    # Compatibility: expose /analyze endpoints at root for older frontend paths
    try:
        from api.routes import analyze_compat

        app.include_router(analyze_compat.router)
    except Exception:
        log.info("Analyze compatibility router not available")
    # stats router (returns aggregated stats at /stats)
    try:
        from api.routes import stats as stats_router

        app.include_router(stats_router.router, prefix="/stats", tags=["stats"])
    except Exception:
        log.info("Stats router not available at startup")
    # auth router (register/login/me)
    try:
        from api.routes import auth as auth_router

        app.include_router(auth_router.router, prefix="/auth", tags=["auth"])
    except Exception:
        log.info("Auth router not available at startup")
    # session router for advanced interview flows
    try:
        from api.routes import session as session_router

        app.include_router(session_router.router)
    except Exception:
        log.info("Session router not available at startup")
    app.include_router(health_router.router)

    @app.on_event("startup")
    def _log_startup():
        from time import perf_counter

        print("startup begin")
        start_ts = perf_counter()
        print("Starting AI Interview Trainer API")
        log.info("Starting AI Interview Trainer API")
        log.info("LOG_LEVEL=%s", LOG_LEVEL)
        log.info("DB_PATH=%s", DB_PATH)
        log.info("STORAGE_DIR=%s", STORAGE_DIR)
        log.info("EMOTION_MODEL=%s", EMOTION_MODEL)

        app.state.model_status = {"emotion": "not_loaded", "pose": "not_loaded", "gaze": "not_loaded"}
        try:
            preload = os.getenv("AIIT_PRELOAD_MODELS", "false").lower() in ("1", "true", "yes")
            if preload:
                try:
                    from ai_models.model_loader import get_emotion_model

                    em = get_emotion_model()
                    app.state.model_status["emotion"] = "loaded" if em is not None else "failed"
                    log.info("Emotion model preload status: %s", app.state.model_status["emotion"])
                except Exception:
                    log.exception("Emotion preload failed")
                    app.state.model_status["emotion"] = "failed"

                try:
                    from ai_models.model_loader import get_pose_model

                    p = get_pose_model()
                    app.state.model_status["pose"] = "loaded" if p is not None else "failed"
                    log.info("Pose model preload status: %s", app.state.model_status["pose"])
                except Exception:
                    log.exception("Pose preload failed")
                    app.state.model_status["pose"] = "failed"

                try:
                    from cv_models.gaze_detector import load_gaze_detector

                    g = load_gaze_detector()
                    app.state.model_status["gaze"] = "loaded" if g is not None else "failed"
                    log.info("Gaze detector preload status: %s", app.state.model_status["gaze"])
                except Exception:
                    log.exception("Gaze preload failed")
                    app.state.model_status["gaze"] = "failed"
            else:
                log.info("Model preload disabled (AIIT_PRELOAD_MODELS not set)")
        except Exception:
            log.exception("Error during model preload/status setup")

        # Ensure DB tables exist and measure time
        try:
            from database.db import init_db

            t0 = perf_counter()
            init_db()
            db_elapsed = perf_counter() - t0
            log.info("Database initialized on startup (%.3fs)", db_elapsed)
            print("db init done (%.3fs)" % db_elapsed)
        except Exception:
            log.exception("Failed to initialize database on startup")

        # Mark router ready and total startup time
        total_elapsed = perf_counter() - start_ts
        log.info("Router ready; startup complete (%.3fs)", total_elapsed)
        print("router ready; startup complete (%.3fs)" % total_elapsed)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
