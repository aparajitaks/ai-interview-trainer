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
    # import user model
    try:
        from . import user_model  # noqa: F401
    except Exception:
        pass

    log.info("Initializing database and creating tables (if not exist)")
    Base.metadata.create_all(bind=engine)

    # Use a simple schema versioning strategy to avoid running ALTERs on every
    # process start. We only run the lightweight additive migrations when the
    # DB user_version is less than our expected schema version. This makes
    # startup cheap on subsequent runs and prevents duplicate-column errors.
    SCHEMA_VERSION = 1
    try:
        with engine.begin() as conn:
            cur = conn.exec_driver_sql("PRAGMA user_version")
            row = cur.fetchone()
            user_version = int(row[0]) if row and row[0] is not None else 0
            log.debug("Current DB user_version=%s, target=%s", user_version, SCHEMA_VERSION)

            if user_version < SCHEMA_VERSION:
                # Lightweight additive migration: inspect tables and only add
                # missing columns. These checks are only performed once per
                # schema version upgrade.
                try:
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
                        # Query adv_interview_sessions columns and add user_id
                        res2 = conn.exec_driver_sql("PRAGMA table_info('adv_interview_sessions')")
                        rows2 = res2.fetchall()
                        sess_cols = [r[1] for r in rows2] if rows2 else []
                        if 'user_id' not in sess_cols:
                            needs.append("ALTER TABLE adv_interview_sessions ADD COLUMN user_id TEXT")
                        for stmt in needs:
                            try:
                                conn.exec_driver_sql(stmt)
                                log.info("Applied DB migration: %s", stmt)
                            except Exception:
                                log.exception("Failed to apply migration statement: %s", stmt)

                    # Migrate users table: add columns added in user_model.py that may
                    # not exist if the DB was created from the old stub User model.
                    res_u = conn.exec_driver_sql("PRAGMA table_info('users')")
                    rows_u = res_u.fetchall()
                    user_cols = [r[1] for r in rows_u] if rows_u else []
                    user_migrations = []
                    if 'email' not in user_cols:
                        user_migrations.append("ALTER TABLE users ADD COLUMN email TEXT")
                    if 'password_hash' not in user_cols:
                        user_migrations.append("ALTER TABLE users ADD COLUMN password_hash TEXT")
                    for stmt in user_migrations:
                        try:
                            conn.exec_driver_sql(stmt)
                            log.info("Applied users migration: %s", stmt)
                        except Exception:
                            log.exception("Failed to apply users migration: %s", stmt)

                    # Bump user_version to mark migrations applied for this schema
                    try:
                        conn.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")
                        log.info("Set DB user_version=%s", SCHEMA_VERSION)
                    except Exception:
                        log.exception("Failed to set PRAGMA user_version=%s", SCHEMA_VERSION)
                except Exception:
                    log.exception("Database migration check/upgrade failed")
            else:
                log.debug("DB schema version is up-to-date; skipping migrations")
    except Exception:
        log.exception("Database migration/version check failed")



if __name__ == "__main__":
    init_db()
    log.info("Database initialized at %s", DB_PATH)
