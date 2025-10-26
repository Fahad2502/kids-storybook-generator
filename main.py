import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
from typing import List
from dotenv import load_dotenv
from passlib.context import CryptContext # For password hashing
from pydantic import Field # For password validation (optional)

# 1. --- Load Environment Variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("gemini_api_key")

if not GEMINI_API_KEY:
    print("\nFATAL ERROR: 'gemini_api_key' NOT FOUND IN .env FILE.\n")
else:
    print("\nAPI key loaded successfully from .env file.\n")

# 2. --- Configure Gemini Client ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    print("Gemini client configured successfully.")
except Exception as e:
    print(f"Error configuring Gemini client: {e}")
    model = None

# 3. --- Database Setup ---
DATABASE_FILE = "stories.db"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Password Helper Functions ---
def verify_password(plain_password: str, hashed_password: str):
    """Verify a password against its hash."""
    truncated_password = plain_password[:72]
    return pwd_context.verify(truncated_password, hashed_password)

def get_password_hash(password: str):
    """Generate a secure hash for a given password, truncated if needed."""
    # bcrypt only supports up to 72 bytes
    truncated_password = password[:72]
    return pwd_context.hash(truncated_password)

# --- END NEW ---
# --- Add NEW User Pydantic Models ---
class UserCreate(BaseModel):
    """Model for data needed to create a new user."""
    username: str
    # Example: Enforce minimum password length using Field
    password: str = Field(..., min_length=8)

class User(BaseModel):
    """Model for returning user info (without the password hash)."""
    id: int
    username: str
    class Config:
        # Allows creating this model from database objects
        from_attributes = True
# --- END NEW ---

# 3. --- Database Setup ---
DATABASE_FILE = "stories.db"

def init_database():
    """Creates/updates the database tables."""
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        cursor = conn.cursor()

        # Create stories table (existing code)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            theme TEXT NOT NULL, story_text TEXT NOT NULL, date TEXT NOT NULL,
            is_favorite INTEGER DEFAULT 0
        )
        """)
        # Add is_favorite column if needed (existing code)
        try: cursor.execute("ALTER TABLE stories ADD COLUMN is_favorite INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass

        # --- NEW: Create users table ---
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,    -- Ensure usernames are unique
            hashed_password TEXT NOT NULL     -- Store the hashed password
        )
        """)
        # --- END NEW ---

        conn.commit()
        conn.close()
        print("Database initialized successfully (stories & users tables checked/created).") # Updated message
    except Exception as e:
        print(f"Error initializing database: {e}")

# 4. --- Define Request/Response Models ---
class StoryRequest(BaseModel):
    name: str
    age: int
    theme: str

class StoryResponse(BaseModel):
    story_id: int | None = None # <-- NEW: Return the ID
    story: str
    debug_feedback: str | None = None


# Models for the 'get-recent-stories' endpoint
class RecentStory(BaseModel):
    # We might add id and is_favorite later if needed for display
    id: int  # <-- ADD THIS
    story_text: str  # <-- ADD THIS
    name: str
    theme: str
    date: str

class RecentStoriesResponse(BaseModel):
    stories: List[RecentStory]

# Model for the favorite response
class FavoriteResponse(BaseModel):
    message: str


# 5. --- Create FastAPI App ---
app = FastAPI(
    title="Kids Story API",
    description="API for generating and retrieving children's stories."
)


@app.on_event("startup")
async def startup_event():
    init_database()


# 6. --- Add CORS Middleware ---
origins = [
    "http://localhost", "http://localhost:8080", "http://127.0.0.1:5500",
    "http://localhost:63342", "null"
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)


# 7. --- Define API Endpoints ---
@app.get("/")
def read_root():
    return {"message": "Kids Story API is running!"}
# --- Add NEW /register Endpoint ---
@app.post("/register", response_model=User, status_code=201)
async def register_user(user: UserCreate):
    """Handles new user registration."""
    # 1. Check if username already exists
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already registered")

    # 2. Hash the password
    hashed_password = get_password_hash(user.password)

    # 3. Insert new user into the database
    try:
        cursor.execute(
            "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
            (user.username, hashed_password)
        )
        user_id = cursor.lastrowid # Get the ID of the new user
        conn.commit()
    except Exception as e:
        conn.rollback() # Undo changes if insert fails
        conn.close()
        print(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Could not register user.")
    finally:
        conn.close() # Ensure connection is always closed

    print(f"User '{user.username}' registered successfully with ID {user_id}.")
    # 4. Return the new user's info (without password)
    return User(id=user_id, username=user.username)
# --- END NEW ---



@app.post("/generate-story", response_model=StoryResponse)
async def generate_story(request: StoryRequest):
    if model is None:
        raise HTTPException(status_code=500, detail="Gemini model is not configured.")

    generated_story = "" # Define outside try block
    new_story_id = None  # Define outside try block

    try:
        # --- MODIFY THE PROMPT HERE ---
        prompt = (
            f"Write a short, magical children's story for a {request.age}-year-old child named {request.name}. "
            f"The story should be about the theme of: {request.theme}. "
            f"Make the story positive, engaging, and easy to read (around 300-400 words). " # <-- Increased word count
            "Do not include a title."
        )
        # --- END PROMPT MODIFICATION ---

        response = await model.generate_content_async(prompt)
        generated_story = response.text.strip()
        debug_info = str(response.prompt_feedback) # Store debug info regardless of errors below

        # --- Save the story to the database ---
        story_date = datetime.now().strftime("%B %d, %Y")
        try:
            conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO stories (name, theme, story_text, date) VALUES (?, ?, ?, ?)",
                (request.name, request.theme, generated_story, story_date)
            )
            new_story_id = cursor.lastrowid # <-- GET THE ID OF THE NEWLY INSERTED ROW
            conn.commit()
            conn.close()
            print(f"New story saved to database with ID: {new_story_id}")
        except Exception as db_e:
            print(f"Database save error: {db_e}")
            # Don't raise error, just return story without ID
            return {"story": generated_story, "debug_feedback": debug_info, "story_id": None}


        # --- Return the generated text, debug info, AND the new ID ---
        return {"story": generated_story, "debug_feedback": debug_info, "story_id": new_story_id}

    except Exception as e:
        print(f"Error generating story: {e}")
        # Return the error message as the story if generation fails
        generated_story = f"Error generating story: {e}"
        return {"story": generated_story, "debug_feedback": None, "story_id": None}

# --- NEW ENDPOINT TO MARK A STORY AS FAVORITE ---
@app.post("/mark-favorite/{story_id}", response_model=FavoriteResponse)
async def mark_story_as_favorite(story_id: int):
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        cursor = conn.cursor()
        # Update the story with the given ID
        cursor.execute("UPDATE stories SET is_favorite = 1 WHERE id = ?", (story_id,))
        conn.commit()

        if cursor.rowcount == 0: # Check if any row was actually updated
             conn.close()
             raise HTTPException(status_code=404, detail=f"Story with ID {story_id} not found.")

        conn.close()
        print(f"Marked story ID {story_id} as favorite.")
        return {"message": f"Story {story_id} marked as favorite."}
    except HTTPException as http_e:
        raise http_e # Re-raise HTTP exceptions
    except Exception as e:
        print(f"Error marking story as favorite: {e}")
        raise HTTPException(status_code=500, detail=f"Could not mark story {story_id} as favorite.")


@app.get("/get-recent-stories", response_model=RecentStoriesResponse)
async def get_recent_stories():
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            # --- CHANGE THIS LINE ---
            "SELECT id, story_text, name, theme, date FROM stories ORDER BY id DESC LIMIT 10"
        )

        recent_stories = cursor.fetchall()
        conn.close()

        stories_list = [dict(story) for story in recent_stories]

        return {"stories": stories_list}

    except Exception as e:
        print(f"Error fetching recent stories: {e}")
        raise HTTPException(status_code=500, detail=f"Database read error: {e}")