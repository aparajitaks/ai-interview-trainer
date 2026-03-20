from __future__ import annotations

import logging
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from config import settings
from database.user_crud import get_user_by_id

log = logging.getLogger(__name__)

_scheme = HTTPBearer(auto_error=False)

SECRET_KEY = getattr(settings, "JWT_SECRET", None) or "change-me-in-prod"
ALGORITHM = getattr(settings, "JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_SECONDS = int(getattr(settings, "JWT_EXPIRE_SECONDS", 60 * 60 * 24))


def create_token(user_id: int, expires_in: Optional[int] = None) -> str:
    now = int(time.time())
    exp = now + (expires_in or ACCESS_TOKEN_EXPIRE_SECONDS)
    payload = {"sub": str(user_id), "iat": now, "exp": exp}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Dict[str, Any]:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data
    except JWTError as exc:
        log.exception("Token verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_scheme)) -> Dict[str, Any]:
    # Allow anonymous access when no Authorization header is provided; preserves
    # existing auth path when a token is present.
    if credentials is None:
        return {}

    token = credentials.credentials
    data = verify_token(token)
    sub = data.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        uid = int(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user id in token")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
