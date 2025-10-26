# backend/models.py
from pydantic import BaseModel, Field
from typing import List, Optional # Use Optional for Python < 3.10 if needed

# --- User Models ---
class UserCreate(BaseModel):
    """Model for data needed to create a new user."""
    username: str
    password: str = Field(..., min_length=8)

class User(BaseModel):
    """Model for returning user info (without the password hash)."""
    id: int
    username: str
    class Config:
        from_attributes = True

# --- Story Models ---
class StoryRequest(BaseModel):
    """Model for incoming story generation requests."""
    name: str
    age: int
    theme: str

class StoryResponse(BaseModel):
    """Model for the response after generating a story."""
    story_id: int | None = None # Use Optional[int] for Python < 3.10
    story: str
    debug_feedback: str | None = None # Use Optional[str] for Python < 3.10

class RecentStory(BaseModel):
    """Model for representing a story in the recent list."""
    id: int
    story_text: str
    name: str
    theme: str
    date: str

class RecentStoriesResponse(BaseModel):
    """Model for the list of recent stories."""
    stories: List[RecentStory]

class FavoriteResponse(BaseModel):
    """Model for the response after marking a story as favorite."""
    message: str

# --- Token Models ---
class Token(BaseModel):
    """Model for the access token response during login."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Model for the data encoded within the JWT token."""
    username: str | None = None # Use Optional[str] for Python < 3.10