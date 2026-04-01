"""
routes/auth.py -- /register and /login endpoints
"""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import create_user, get_user_by_username, get_user_by_email
from backend.auth import hash_password, verify_password, create_token

router = APIRouter()


class RegisterRequest(BaseModel):
    first_name: str
    last_name:  str
    email:      str
    username:   str
    password:   str


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(data: RegisterRequest):
    # Validate first/last name
    if len(data.first_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="First name must be at least 2 characters")
    if len(data.last_name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Last name must be at least 2 characters")

    # Validate email format
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', data.email.strip()):
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Validate username — only letters, numbers, underscores, 3-20 chars
    username = data.username.strip()
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        raise HTTPException(status_code=400, detail="Username must be 3-20 characters, letters/numbers/underscore only")

    # Validate password strength
    pwd = data.password
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not re.search(r'[A-Z]', pwd):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not re.search(r'[0-9]', pwd):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")

    # Check duplicates
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already taken")
    if get_user_by_email(data.email.strip().lower()):
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = create_user(
        username=username,
        hashed_password=hash_password(pwd),
        email=data.email.strip().lower(),
        first_name=data.first_name.strip(),
        last_name=data.last_name.strip(),
    )
    token = create_token(user_id, username)
    return {"token": token, "username": username, "user_id": user_id,
            "first_name": data.first_name.strip()}


@router.post("/login")
async def login(data: LoginRequest):
    user = get_user_by_username(data.username.strip())
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(user["id"], user["username"])
    return {"token": token, "username": user["username"], "user_id": user["id"],
            "first_name": user.get("first_name", user["username"])}


@router.get("/me")
async def me(authorization: str = None):
    if not authorization:
        return {"logged_in": False}
    from backend.auth import decode_token
    try:
        payload = decode_token(authorization.replace("Bearer ", ""))
        return {"logged_in": True, "username": payload["username"], "user_id": payload["sub"]}
    except Exception:
        return {"logged_in": False}
