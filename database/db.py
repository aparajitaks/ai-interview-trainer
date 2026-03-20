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


def add_column_if_not_exists(cursor, table: str, column: str, definition: str) -> bool:
    """Add a column to a SQLite table if it does not already exist.

    Uses ``PRAGMA table_info`` to inspect existing columns before issuing
    the ALTER TABLE statement. Returns True if a column was added, False
    if it already existed or the table was missing.
    """

    if not table or not column or not definition:
        return False

    cursor.execute(f"PRAGMA table_info('{table}')")
    rows = cursor.fetchall() or []
    cols = [r[1] for r in rows]
    if column in cols:
        return False

    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    return True


def init_db() -> None:
    """Create database tables. Call at application startup or in tests."""
    from . import models  # ensure models are imported so they are registered on Base
    # import advanced models for the session system
    try:
        from . import advanced_models  # noqa: F401
    except Exception:
        # advanced models may not exist in older versions; ignore failures
        pass
    # import user model
    try:
        from . import user_model  # noqa: F401
    except Exception:
        pass

    log.info("Initializing database and creating tables (if not exist)")
    Base.metadata.create_all(bind=engine)
    # Lightweight additive migration: if advanced answers table exists but lacks
    # newly added columns, add them so the application can upgrade in-place.
    try:
        # Use a transaction so DDL changes are committed atomically.
        with engine.begin() as conn:
            cursor = conn.connection.cursor()
            try:
                # adv_interview_answers migrations
                if add_column_if_not_exists(cursor, "adv_interview_answers", "answer_text", "TEXT"):
                    log.info("Applied DB migration: adv_interview_answers.answer_text")
                if add_column_if_not_exists(cursor, "adv_interview_answers", "keywords", "TEXT"):
                    log.info("Applied DB migration: adv_interview_answers.keywords")
                if add_column_if_not_exists(cursor, "adv_interview_answers", "feedback", "TEXT"):
                    log.info("Applied DB migration: adv_interview_answers.feedback")

                # adv_interview_sessions.user_id
                if add_column_if_not_exists(cursor, "adv_interview_sessions", "user_id", "TEXT"):
                    log.info("Applied DB migration: adv_interview_sessions.user_id")

                # users table migrations
                if add_column_if_not_exists(cursor, "users", "email", "TEXT"):
                    log.info("Applied users migration: users.email")
                if add_column_if_not_exists(cursor, "users", "password_hash", "TEXT"):
                    log.info("Applied users migration: users.password_hash")
            finally:
                cursor.close()
    except Exception:
        log.exception("Database migration check failed")



if __name__ == "__main__":
    init_db()
    log.info("Database initialized at %s", DB_PATH)
