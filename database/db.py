"""Database connection and base for AI Interview Trainer.

Creates a SQLite engine and a SessionLocal factory. Other modules import
``Base`` to declare models.
"""

from __future__ import annotations

import logging
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Database file location (in-repo). In production move to config/env.
DB_PATH = os.environ.get("AIIT_DB_PATH", os.path.join(os.getcwd(), "storage", "ai_interview.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQLite engine. check_same_thread False for multi-threaded apps; safe here.
ENGINE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(ENGINE_URL, connect_args={"check_same_thread": False}, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models
Base = declarative_base()


def init_db() -> None:
    """Create database tables. Call at application startup or in tests."""
    from . import models  # ensure models are imported so they are registered on Base

    log.info("Initializing database and creating tables (if not exist)")
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    log.info("Database initialized at %s", DB_PATH)
