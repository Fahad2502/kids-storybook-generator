"""
JWT authentication helpers.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import HTTPException, Header
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "kids-story-secret-change-in-production-2025")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict | None:
    """Extract and verify user from Authorization header. Returns None if unauthenticated."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        return decode_token(token)
    except HTTPException:
        return None


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Require a valid Authorization header, raising 401 if absent or invalid."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user
