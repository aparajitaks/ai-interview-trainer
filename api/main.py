"""FastAPI application for AI Interview Trainer.

Includes interview and results routers. This module creates an app and
initializes shared components used by routes.
"""

from __future__ import annotations

import logging
from config.settings import LOG_LEVEL

from fastapi import FastAPI

from api.routes import interview as interview_router
from api.routes import results as results_router

log = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


def create_app() -> FastAPI:
    app = FastAPI(title="AI Interview Trainer API")

    # Include routers
    app.include_router(interview_router.router, prefix="/interview", tags=["interview"])
    app.include_router(results_router.router, prefix="/results", tags=["results"])

    return app


app = create_app()


if __name__ == "__main__":
    # Simple run for local testing. Use `uvicorn api.main:app` in production.
    import uvicorn

    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
