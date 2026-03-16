from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from database import crud

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()


@router.get("/")
def get_stats():
    try:
        try:
            s = crud.get_stats()
        except Exception:
            log.exception("Failed to compute stats from DB")
            raise HTTPException(status_code=500, detail="DB read failed")
        return s
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Unhandled error in get_stats: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error")
