from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from database.db import SessionLocal
from database.user_model import User
import logging

log = logging.getLogger(__name__)

try:
    from passlib.context import CryptContext

    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    _pwd_ctx = None


def create_user(username: str, email: str, password: str) -> User:
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter((User.email == email) | (User.username == username)).first()
        if existing:
            raise ValueError("User with that email or username already exists")

        if _pwd_ctx is not None:
            ph = _pwd_ctx.hash(password)
        else:
            # fallback (insecure) - store raw password (not recommended)
            ph = password

        u = User(username=username, email=email, password_hash=ph)
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        u = db.query(User).filter_by(email=email).first()
        if not u:
            return None
        return {"id": u.id, "username": u.username, "email": u.email, "password_hash": u.password_hash}
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    db: Session = SessionLocal()
    try:
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return None
        return {"id": u.id, "username": u.username, "email": u.email, "password_hash": u.password_hash}
    finally:
        db.close()


def verify_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    ph = user.get("password_hash")
    if _pwd_ctx is not None:
        try:
            if _pwd_ctx.verify(password, ph):
                return user
        except Exception:
            return None
    else:
        # fallback insecure compare
        if password == ph:
            return user
    return None
