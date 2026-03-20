from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from database import user_crud
from auth.jwt_handler import create_token, get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/register")
def register(req: RegisterRequest):
    try:
        u = user_crud.create_user(req.username, req.email, req.password)
        token = create_token(u.id)
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.post("/auth/login")
def login(req: LoginRequest):
    u = user_crud.verify_user(req.email, req.password)
    if not u:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(int(u["id"]))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
def me(current_user: dict = Depends(get_current_user)):
    # return non-sensitive user info
    return {"id": current_user.get("id"), "username": current_user.get("username"), "email": current_user.get("email")}
