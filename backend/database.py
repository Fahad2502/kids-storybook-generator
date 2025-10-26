# backend/database.py
import sqlite3

DATABASE_FILE = "stories.db" # Path relative to this file (up one level)

def init_database():
    """Creates/updates the database tables."""
    try:
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        cursor = conn.cursor()
        # Create stories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            theme TEXT NOT NULL, story_text TEXT NOT NULL, date TEXT NOT NULL,
            is_favorite INTEGER DEFAULT 0
        )
        """)
        # Add is_favorite column if needed
        try: cursor.execute("ALTER TABLE stories ADD COLUMN is_favorite INTEGER DEFAULT 0")
        except sqlite3.OperationalError: pass # Ignore if column exists

        # Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL
        )
        """)

        conn.commit()
        conn.close()
        print("Database initialized successfully (stories & users tables checked/created).")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Function to get a database connection
def get_db_connection():
    """Returns a new database connection."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row # Return rows that act like dictionaries
    return conn