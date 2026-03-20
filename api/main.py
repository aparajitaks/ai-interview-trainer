"""FastAPI application for AI Interview Trainer.

Includes interview and results routers. This module creates an app and
initializes shared components used by routes.
"""

from __future__ import annotations

import logging
import os
from dotenv import load_dotenv
from config.settings import LOG_LEVEL, DB_PATH, STORAGE_DIR, EMOTION_MODEL
from utils.logger import get_logger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import interview as interview_router
from api.routes import results as results_router
from api.routes import health as health_router

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MODEL_OFFLINE = os.getenv("MODEL_OFFLINE", "").lower() in ("1", "true", "yes")

if MODEL_OFFLINE:
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

log = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Interview Trainer API")

    # Allow frontend dev server origins for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://localhost",
            "http://127.0.0.1",
        ],
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
        print("startup begin")
        print("Starting AI Interview Trainer API")
        log.info("Starting AI Interview Trainer API")
        log.info("LOG_LEVEL=%s", LOG_LEVEL)
        log.info("DB_PATH=%s", DB_PATH)
        log.info("STORAGE_DIR=%s", STORAGE_DIR)
        log.info("EMOTION_MODEL=%s", EMOTION_MODEL)
        log.info("HOST=%s PORT=%s", HOST, PORT)
        if MODEL_OFFLINE:
            log.info("MODEL_OFFLINE enabled; transformers offline")

        app.state.model_status = {"emotion": "lazy", "pose": "lazy", "gaze": "lazy"}
        log.info("Model preload disabled; models will load lazily on first use")

        # Ensure DB tables exist
        try:
            from database.db import init_db

            init_db()
            log.info("Database initialized on startup")
            print("db init done")
        except Exception:
            log.exception("Failed to initialize database on startup")

        print("router ready")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host=HOST, port=PORT)
