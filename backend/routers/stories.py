# backend/routers/stories.py
import sqlite3
from typing import List

from fastapi import APIRouter, HTTPException
import google.generativeai as genai

# Import functions and models from our other backend files
from .. import models # Use .. to go up one level from routers to backend
from .. import auth # We might need auth later
from ..database import get_db_connection, DATABASE_FILE

# --- Configure Gemini Client ---
# (We need to re-configure Gemini here or pass the model instance)
# For simplicity now, let's re-configure. Consider passing the model via dependency later.
try:
    # --- CHANGE: Use the imported key directly ---
    if auth.GEMINI_API_KEY:
        genai.configure(api_key=auth.GEMINI_API_KEY)
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        print("Gemini client configured successfully in stories.py.")
    # --- END CHANGE ---
    else:
        print("GEMINI_API_KEY not found in auth module. Story generation will fail.")
        model = None
except Exception as e:
    print(f"Error configuring Gemini client in stories.py: {e}")
    model = None
# --- End Gemini Config ---

# Create a router for story-related endpoints
router = APIRouter(
    prefix="/stories", # All routes in this file will start with /stories
    tags=["stories"], # Tag for grouping in API docs
)

# --- Generate Story Endpoint ---
@router.post("/generate", response_model=models.StoryResponse)
async def generate_story(request: models.StoryRequest):
    """Generates a new story using the Gemini model."""
    if model is None:
        raise HTTPException(status_code=500, detail="Gemini model is not configured.")

    generated_story = ""
    new_story_id = None
    debug_info = None

    try:
        prompt = (
            f"Write a short, magical children's story for a {request.age}-year-old child named {request.name}. "
            f"The story should be about the theme of: {request.theme}. "
            f"Make the story positive, engaging, and easy to read (around 300-400 words). "
            "Do not include a title."
        )

        response = await model.generate_content_async(prompt)
        generated_story = response.text.strip()
        debug_info = str(response.prompt_feedback)

        # Save the story
        story_date = auth.datetime.now().strftime("%B %d, %Y") # Use datetime from auth
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stories (name, theme, story_text, date) VALUES (?, ?, ?, ?)",
                (request.name, request.theme, generated_story, story_date)
            )
            new_story_id = cursor.lastrowid
            conn.commit()
            print(f"New story saved to database with ID: {new_story_id}")
        except Exception as db_e:
            conn.rollback()
            print(f"Database save error: {db_e}")
            # Still return the story, but indicate save failed by missing ID
            return models.StoryResponse(story=generated_story, debug_feedback=debug_info, story_id=None)
        finally:
            conn.close()

        return models.StoryResponse(story=generated_story, debug_feedback=debug_info, story_id=new_story_id)

    except Exception as e:
        print(f"Error generating story: {e}")
        # Return error message as story content if generation fails
        generated_story = f"Error generating story: {e}"
        return models.StoryResponse(story=generated_story, debug_feedback=debug_info, story_id=None)


# --- Mark as Favorite Endpoint ---
@router.post("/mark-favorite/{story_id}", response_model=models.FavoriteResponse)
async def mark_story_as_favorite(story_id: int):
    """Marks a specific story as a favorite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE stories SET is_favorite = 1 WHERE id = ?", (story_id,))
        conn.commit()

        if cursor.rowcount == 0:
             raise HTTPException(status_code=404, detail=f"Story with ID {story_id} not found.")

        print(f"Marked story ID {story_id} as favorite.")
        return models.FavoriteResponse(message=f"Story {story_id} marked as favorite.")
    except HTTPException as http_e:
        raise http_e # Re-raise known HTTP errors
    except Exception as e:
        conn.rollback()
        print(f"Error marking story {story_id} as favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Could not mark story {story_id} as favorite.")
    finally:
        conn.close()


# --- Get Recent Stories Endpoint ---
@router.get("/recent", response_model=models.RecentStoriesResponse)
async def get_recent_stories():
    """Retrieves the 10 most recently created stories."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, story_text, name, theme, date FROM stories ORDER BY id DESC LIMIT 10"
        )
        recent_stories_rows = cursor.fetchall()
        # Convert rows to list of dicts suitable for Pydantic model
        stories_list = [dict(row) for row in recent_stories_rows]
        return models.RecentStoriesResponse(stories=stories_list)
    except Exception as e:
        print(f"Error fetching recent stories: {e}")
        raise HTTPException(status_code=500, detail=f"Database read error: {e}")
    finally:
        conn.close()

print("Backend routers/stories.py loaded.") # Confirmation

# --- NEW: Get Favorite Stories Endpoint ---
@router.get("/favorites", response_model=models.RecentStoriesResponse) # Reuse same response model
async def get_favorite_stories():
    """Retrieves all stories marked as favorite."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Select stories where is_favorite is 1 (True)
        cursor.execute(
            "SELECT id, story_text, name, theme, date FROM stories WHERE is_favorite = 1 ORDER BY id DESC"
        )
        favorite_stories_rows = cursor.fetchall()
        # Convert rows to list of dicts
        stories_list = [dict(row) for row in favorite_stories_rows]
        return models.RecentStoriesResponse(stories=stories_list)
    except Exception as e:
        print(f"Error fetching favorite stories: {e}")
        # Use a specific detail message for favorites error
        raise HTTPException(status_code=500, detail=f"Database error fetching favorites: {e}")
    finally:
        if conn:
            conn.close()
# --- END NEW ---