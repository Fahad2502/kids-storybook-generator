"""
auth.py -- JWT authentication helpers
"""
import os
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Header
from typing import Optional

SECRET_KEY = os.getenv("SECRET_KEY", "kids-story-secret-change-in-production-2025")
ALGORITHM  = "HS256"
TOKEN_EXPIRE_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict | None:
    """Extract user from Authorization header. Returns None if not logged in."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]
    try:
        return decode_token(token)
    except HTTPException:
        return None


def require_auth(authorization: Optional[str] = Header(None)) -> dict:
    """Like get_current_user but raises 401 if not logged in."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    return user
