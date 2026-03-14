"""Routes to fetch stored results for sessions."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from database import crud

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.get("/session/{session_id}")
def get_session_results(session_id: str):
    try:
        s = crud.get_session(session_id)
    except Exception:
        log.exception("Failed to read session from DB: %s", session_id)
        raise HTTPException(status_code=500, detail="DB read failed")
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s
