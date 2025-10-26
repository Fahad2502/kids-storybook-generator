# backend/auth.py
import os
import sqlite3
from datetime import datetime, timedelta, timezone # Added timezone for consistency
from typing import Annotated # For newer type hinting with Depends

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- Configuration ---
load_dotenv() # Load .env file from the main project directory
GEMINI_API_KEY = os.getenv("gemini_api_key")
DATABASE_FILE = "../stories.db" # Path relative to this file

# JWT Settings (Consider moving SECRET_KEY to .env for production)
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-please-change") # Load from .env or use default
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 # Token validity duration

# Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 Scheme Setup (Defines how clients send tokens)
# tokenUrl should match the path of your login endpoint (which we'll create later)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

# --- Password Helper Functions ---
def verify_password(plain_password: str, hashed_password: str):
    """Verify a plain password against its stored hash."""
    # Truncate plain password before verification for consistency with hashing
    plain_bytes = plain_password.encode('utf-8')[:72]
    try:
        return pwd_context.verify(plain_bytes, hashed_password)
    except Exception as e:
        print(f"Error verifying password: {e}") # Log potential errors
        return False

def get_password_hash(password: str):
    """Generate a secure hash for a given password, truncated if needed."""
    # Bcrypt requires passwords to be <= 72 bytes. Encode to bytes and truncate.
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes)

# --- Token Helper Functions ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiry time if none provided
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Database Helper for Authentication ---
def get_user(username: str):
    """Fetches a user by username from the database. Returns user dict or None."""
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row # Return rows that act like dicts
        cursor = conn.cursor()
        # Fetch user including the hashed password
        cursor.execute("SELECT id, username, hashed_password FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if user_row:
            return dict(user_row) # Convert Row object to dict
        return None
    except Exception as e:
        print(f"Error fetching user '{username}': {e}")
        return None # Return None on error
    finally:
        if conn:
            conn.close() # Ensure connection is closed

# --- Dependency for Getting Current User (We'll use this later) ---
# This function will be used in endpoints that require authentication
# async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#     credentials_exception = HTTPException(
#         status_code=401, # Unauthorized
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str | None = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#         token_data = {"username": username} # Simplified TokenData for this example
#     except JWTError:
#         raise credentials_exception
#     user = get_user(username=token_data["username"])
#     if user is None:
#         raise credentials_exception
#     # Return user data (e.g., as a dict or Pydantic model)
#     # For now, just return the username dict for simplicity
#     return {"username": user["username"], "id": user["id"]}

print("Backend auth.py loaded.") # Confirmation message