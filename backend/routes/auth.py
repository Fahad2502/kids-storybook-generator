"""
routes/auth.py -- /register and /login endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import create_user, get_user_by_username
from backend.auth import hash_password, verify_password, create_token

router = APIRouter()


class AuthRequest(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(data: AuthRequest):
    username = data.username.strip()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(data.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if username taken
    if get_user_by_username(username):
        raise HTTPException(status_code=409, detail="Username already taken")

    user_id = create_user(username, hash_password(data.password))
    token = create_token(user_id, username)
    return {"token": token, "username": username, "user_id": user_id}


@router.post("/login")
async def login(data: AuthRequest):
    user = get_user_by_username(data.username.strip())
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user["id"], user["username"])
    return {"token": token, "username": user["username"], "user_id": user["id"]}


@router.get("/me")
async def me(authorization: str = None):
    """Check if token is valid and return user info."""
    from fastapi import Header
    from backend.auth import get_current_user
    # This is called from frontend to verify token on page load
    if not authorization:
        return {"logged_in": False}
    from backend.auth import decode_token
    try:
        payload = decode_token(authorization.replace("Bearer ", ""))
        return {"logged_in": True, "username": payload["username"], "user_id": payload["sub"]}
    except Exception:
        return {"logged_in": False}
