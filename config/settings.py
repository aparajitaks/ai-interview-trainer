"""Application settings loaded from environment variables.

This module centralizes configuration values so other modules import
from a single place. Values are loaded with ``os.getenv`` and have
reasonable defaults for local development.
"""
from __future__ import annotations

import logging
import os
from typing import Final
from dotenv import load_dotenv

# Load .env file if present so environment variables can be provided via a
# project-local .env during development. This is a no-op if no .env exists
# and preserves existing behavior which uses os.getenv.
load_dotenv()

# Emotion model to use with the HF transformers pipeline
EMOTION_MODEL: Final[str] = os.getenv("EMOTION_MODEL", "microsoft/resnet-50")

# Where to store uploaded videos (default: ./storage/video)
STORAGE_DIR: Final[str] = os.getenv("AIIT_STORAGE_DIR", os.path.join(os.getcwd(), "storage", "video"))

# Database path for SQLite (default: ./storage/ai_interview.db)
DB_PATH: Final[str] = os.getenv("AIIT_DB_PATH", os.path.join(os.getcwd(), "storage", "ai_interview.db"))

# Directory for extracted frames (default: ./storage/frames)
FRAME_DIR: Final[str] = os.getenv("AIIT_FRAME_DIR", os.path.join(os.getcwd(), "storage", "frames"))

# Logging level (string like 'INFO', 'DEBUG'). We convert to logging level int
_LOG_LEVEL_NAME = os.getenv("AIIT_LOG_LEVEL", "INFO").upper()
try:
    LOG_LEVEL: Final[int] = getattr(logging, _LOG_LEVEL_NAME)
except Exception:
    LOG_LEVEL = logging.INFO

# Ensure directory components exist where sensible (caller may still create)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)
