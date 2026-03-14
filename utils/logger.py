"""Global logger configuration for AI Interview Trainer.

Provides a single entrypoint to get configured loggers across the app.
Configuration is read from config.settings.LOG_LEVEL so behavior can be
controlled via environment variables.
"""
from __future__ import annotations

import logging
from typing import Any

from config.settings import LOG_LEVEL


def _configure_root_logger() -> None:
    root = logging.getLogger()
    # Avoid reconfiguring if already set up
    if root.handlers:
        return
    root.setLevel(LOG_LEVEL)
    handler = logging.StreamHandler()
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger configured with the global settings.

    Args:
        name: logger name (typically __name__). If None, return root logger.
    """
    _configure_root_logger()
    return logging.getLogger(name)
