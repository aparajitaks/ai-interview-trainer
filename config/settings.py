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

load_dotenv()

EMOTION_MODEL: Final[str] = os.getenv("EMOTION_MODEL", "microsoft/resnet-50")

STORAGE_DIR: Final[str] = os.getenv("AIIT_STORAGE_DIR", os.path.join(os.getcwd(), "storage", "video"))

DB_PATH: Final[str] = os.getenv("AIIT_DB_PATH", os.path.join(os.getcwd(), "storage", "ai_interview.db"))

FRAME_DIR: Final[str] = os.getenv("AIIT_FRAME_DIR", os.path.join(os.getcwd(), "storage", "frames"))

try:
    SAMPLE_FRAMES: Final[int] = int(os.getenv("AIIT_SAMPLE_FRAMES", "5"))
except Exception:
    SAMPLE_FRAMES = 5

_LOG_LEVEL_NAME = os.getenv("AIIT_LOG_LEVEL", "INFO").upper()
try:
    LOG_LEVEL: Final[int] = getattr(logging, _LOG_LEVEL_NAME)
except Exception:
    LOG_LEVEL = logging.INFO

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)
