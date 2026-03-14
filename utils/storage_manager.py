from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

from config.settings import STORAGE_DIR, LOG_LEVEL

log = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL)


def get_storage_dir() -> Path:
    """Return the absolute path to the storage/video directory.

    The storage directory is located at the repository root under
    ./storage/video. This function creates the directory if it does not
    exist.
    """
    # STORAGE_DIR from config can be absolute or relative; resolve and create
    storage_dir = Path(STORAGE_DIR).resolve()
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        log.error("Failed to create storage directory: %s", storage_dir, exc_info=True)
        raise
    return storage_dir


def generate_filename(ext: str = "mp4") -> str:
    """Generate a unique filename using timestamp and UUID.

    Args:
        ext: File extension without leading dot (default: 'mp4').

    Returns:
        A safe filename string like '20260314T123456_4f3a2b.mp4'.
    """
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:8]
    ext_clean = ext.lstrip(".")
    return f"{ts}_{uid}.{ext_clean}"


def save_video(file_bytes: Union[bytes, bytearray], filename: str) -> Path:
    """Save bytes to storage/video safely and return the saved file Path.

    The function performs an atomic write by first writing to a temporary
    file in the destination directory and then renaming it to the final
    filename. The destination directory will be created if missing.

    Args:
        file_bytes: Raw file content as bytes or bytearray.
        filename: Desired filename (basename only). Any path components
            provided will be ignored for safety.

    Returns:
        Path to the saved file.
    """
    if not isinstance(file_bytes, (bytes, bytearray)):
        log.error("save_video expected bytes-like content, got %s", type(file_bytes))
        raise TypeError("file_bytes must be bytes or bytearray")

    storage_dir = get_storage_dir()
    safe_name = Path(filename).name  # strip any path components
    target_path = storage_dir / safe_name

    # If file exists, append a short suffix to avoid overwriting
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        new_name = f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"
        target_path = storage_dir / new_name

    # Write to a temp file in the same directory and rename to ensure atomicity
    try:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(storage_dir)) as tmp:
            tmp.write(file_bytes)
            tmp.flush()
            tmp_path = Path(tmp.name)
        tmp_path.replace(target_path)
    except Exception:
        log.error("Failed to save video to %s", target_path, exc_info=True)
        # Clean up temp file if it still exists
        try:
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            log.error("Failed to clean up temporary file %s", tmp_path, exc_info=True)
        raise

    log.info("Saved video to: %s", target_path)
    return target_path


if __name__ == "__main__":
    # Simple test main: write a small dummy file and log the saved path.
    TEST_BYTES = b"\x00\x01\x02dummy video data\x03\x04"
    test_name = generate_filename(ext="mp4")
    try:
        saved = save_video(TEST_BYTES, test_name)
        log.info("Test save complete: %s", saved)
    except Exception as exc:
        log.error("Test save failed: %s", exc, exc_info=True)