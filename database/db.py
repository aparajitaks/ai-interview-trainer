"""Database connection and base for AI Interview Trainer.

Creates a SQLite engine and a SessionLocal factory. Other modules import
``Base`` to declare models.
"""

from __future__ import annotations

import logging
import os
from config.settings import DB_PATH, LOG_LEVEL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

log = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

ENGINE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(ENGINE_URL, connect_args={"check_same_thread": False}, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db() -> None:
    """Create database tables. Call at application startup or in tests."""
    from . import models  # ensure models are imported so they are registered on Base
    # import advanced models for the session system
    try:
        from . import advanced_models  # noqa: F401
    except Exception:
        # advanced models may not exist in older versions; ignore failures
        pass

    log.info("Initializing database and creating tables (if not exist)")
    Base.metadata.create_all(bind=engine)
    # Lightweight additive migration: if advanced answers table exists but lacks
    # newly added columns, add them so the application can upgrade in-place.
    try:
        with engine.connect() as conn:
            # Check adv_interview_answers columns using driver-level SQL
            res = conn.exec_driver_sql("PRAGMA table_info('adv_interview_answers')")
            rows = res.fetchall()
            cols = [r[1] for r in rows] if rows else []
            if 'adv_interview_answers' in [t.name for t in Base.metadata.sorted_tables] and cols:
                needs = []
                if 'answer_text' not in cols:
                    needs.append("ALTER TABLE adv_interview_answers ADD COLUMN answer_text TEXT")
                if 'keywords' not in cols:
                    needs.append("ALTER TABLE adv_interview_answers ADD COLUMN keywords TEXT")
                if 'feedback' not in cols:
                    needs.append("ALTER TABLE adv_interview_answers ADD COLUMN feedback TEXT")
                for stmt in needs:
                    try:
                        conn.exec_driver_sql(stmt)
                        log.info("Applied DB migration: %s", stmt)
                    except Exception:
                        log.exception("Failed to apply migration statement: %s", stmt)
    except Exception:
        log.exception("Database migration check failed")


if __name__ == "__main__":
    init_db()
    log.info("Database initialized at %s", DB_PATH)
