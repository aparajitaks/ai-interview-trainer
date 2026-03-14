"""FastAPI application for AI Interview Trainer.

Includes interview and results routers. This module creates an app and
initializes shared components used by routes.
"""

from __future__ import annotations

import logging
from config.settings import LOG_LEVEL, DB_PATH, STORAGE_DIR, EMOTION_MODEL
from utils.logger import get_logger

from fastapi import FastAPI

from api.routes import interview as interview_router
from api.routes import results as results_router
from api.routes import health as health_router

log = get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Interview Trainer API")

    # Include routers
    app.include_router(interview_router.router, prefix="/interview", tags=["interview"])
    app.include_router(results_router.router, prefix="/results", tags=["results"])
    app.include_router(health_router.router)

    # Log startup configuration for observability
    @app.on_event("startup")
    def _log_startup():
        log.info("Starting AI Interview Trainer API")
        log.info("LOG_LEVEL=%s", LOG_LEVEL)
        log.info("DB_PATH=%s", DB_PATH)
        log.info("STORAGE_DIR=%s", STORAGE_DIR)
        log.info("EMOTION_MODEL=%s", EMOTION_MODEL)

    return app


app = create_app()


if __name__ == "__main__":
    # Simple run for local testing. Use `uvicorn api.main:app` in production.
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
