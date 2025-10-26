# backend/routers/users.py
import sqlite3
from typing import Annotated # For newer type hinting with Depends

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

# Import functions and models from our other backend files
from .. import models # Use .. to go up one level from routers to backend
from .. import auth
from ..database import get_db_connection, DATABASE_FILE

# Create a router for user-related endpoints
router = APIRouter(
    prefix="/users", # All routes in this file will start with /users
    tags=["users"], # Tag for grouping in API docs
)

# --- Registration Endpoint ---
@router.post("/register", response_model=models.User, status_code=201)
async def register_user(user: models.UserCreate):
    """Handles new user registration."""
    # 1. Check if username already exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")

    # 2. Hash the password
    hashed_password = auth.get_password_hash(user.password)

    # 3. Insert new user into the database
    try:
        cursor.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (user.username, hashed_password)
        )
        user_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Could not register user.")
    finally:
        conn.close()

    print(f"User '{user.username}' registered successfully with ID {user_id}.")
    # 4. Return the new user's info
    return models.User(id=user_id, username=user.username)

# --- Login Endpoint (using /token path relative to /users prefix) ---
@router.post("/token", response_model=models.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    """Handles user login and returns an access token."""
    user = auth.get_user(form_data.username) # Use helper from auth.py

    if not user or not auth.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Create token
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    print(f"User '{user['username']}' logged in successfully.")
    return {"access_token": access_token, "token_type": "bearer"}

print("Backend routers/users.py loaded.") # Confirmation message