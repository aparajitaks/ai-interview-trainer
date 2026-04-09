"""
logger.py
---------
Centralized logging factory for the AI Interview Trainer project.

Provides a reusable, configurable logger that writes structured output
to both the console and (optionally) a rotating log file. All modules
in this project consume a logger via `get_logger(__name__)`.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_DEFAULT_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def get_logger(
    name: str,
    level: int = logging.DEBUG,
    log_to_file: bool = True,
    log_filename: str = "app.log",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """
    Create (or retrieve) a named logger with consistent formatting.

    If a logger with the given name already has handlers attached it is
    returned as-is, preventing duplicate log entries when the same module
    is imported multiple times.

    Args:
        name:          Logger name, typically ``__name__`` of the caller.
        level:         Minimum logging level (default: ``logging.DEBUG``).
        log_to_file:   Whether to attach a ``RotatingFileHandler``.
        log_filename:  Name of the log file (placed inside ``logs/``).
        max_bytes:     Maximum size of a single log file before rotation.
        backup_count:  Number of rotated backup files to keep.
        fmt:           Custom format string; falls back to ``_DEFAULT_FORMAT``.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers (e.g. on hot-reload / re-import).
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(fmt or _DEFAULT_FORMAT, datefmt=_DATE_FORMAT)

    # --- Console handler ---------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Rotating file handler --------------------------------------------
    if log_to_file:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            _LOG_DIR / log_filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to the root logger to avoid duplicate output.
    logger.propagate = False

    return logger
