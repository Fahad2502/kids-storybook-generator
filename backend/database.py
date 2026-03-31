"""
database.py -- Database connection helper
Supports SQLite (local dev) and PostgreSQL (production).
Set DATABASE_URL in .env for PostgreSQL, otherwise uses SQLite.
"""
import json
import os
from datetime import datetime
from backend.config import DATABASE_PATH

# Detect if PostgreSQL is available
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    print(f"Using PostgreSQL database")
else:
    import sqlite3
    print(f"Using SQLite database: {DATABASE_PATH}")


def get_conn():
    """Return a new database connection."""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return __import__("sqlite3").connect(DATABASE_PATH)


def _placeholder(n: int) -> str:
    """Return correct placeholders for the DB driver."""
    if USE_POSTGRES:
        return ", ".join(f"${i}" for i in range(1, n + 1))
    return ", ".join(["?"] * n)


def init_database() -> None:
    """Create the stories table if it doesn't exist."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id          SERIAL PRIMARY KEY,
                    name        TEXT    NOT NULL,
                    theme       TEXT    NOT NULL,
                    full_text   TEXT    NOT NULL,
                    is_favorite INTEGER DEFAULT 0,
                    date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating      INTEGER DEFAULT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_images (
                    story_id    INTEGER NOT NULL,
                    page_num    INTEGER NOT NULL,
                    image_url   TEXT    NOT NULL,
                    PRIMARY KEY (story_id, page_num)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    theme       TEXT    NOT NULL,
                    full_text   TEXT    NOT NULL,
                    is_favorite INTEGER DEFAULT 0,
                    date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating      INTEGER DEFAULT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_images (
                    story_id    INTEGER NOT NULL,
                    page_num    INTEGER NOT NULL,
                    image_url   TEXT    NOT NULL,
                    PRIMARY KEY (story_id, page_num)
                )
            """)
            # SQLite migrations for older DBs
            cur.execute("PRAGMA table_info(stories)")
            cols = [c[1] for c in cur.fetchall()]
            for col, sql in {
                "rating": "ALTER TABLE stories ADD COLUMN rating INTEGER DEFAULT NULL",
            }.items():
                if col not in cols:
                    cur.execute(sql)
                    print(f"Migrated: added '{col}' column")
        conn.commit()
        print("Database ready")
    finally:
        conn.close()


def save_image_url(story_id: int, page_num: int, image_url: str) -> None:
    """Save a generated image URL for a story page."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO story_images (story_id, page_num, image_url) VALUES (%s, %s, %s) "
                "ON CONFLICT (story_id, page_num) DO UPDATE SET image_url = EXCLUDED.image_url",
                (story_id, page_num, image_url)
            )
        else:
            cur.execute(
                "INSERT OR REPLACE INTO story_images (story_id, page_num, image_url) VALUES (?, ?, ?)",
                (story_id, page_num, image_url)
            )
        conn.commit()
    finally:
        conn.close()


def get_image_url(story_id: int, page_num: int) -> str | None:
    """Get a cached image URL for a story page. Returns None if not found."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "SELECT image_url FROM story_images WHERE story_id = %s AND page_num = %s",
                (story_id, page_num)
            )
        else:
            cur.execute(
                "SELECT image_url FROM story_images WHERE story_id = ? AND page_num = ?",
                (story_id, page_num)
            )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def save_story(name: str, theme: str, story_data: dict) -> int:
    """Insert a new story and return its auto-generated ID."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, theme, json.dumps(story_data, default=str), datetime.now())
            )
            story_id = cur.fetchone()[0]
        else:
            cur.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
                (name, theme, json.dumps(story_data, default=str), datetime.now())
            )
            story_id = cur.lastrowid
        conn.commit()
        return story_id
    finally:
        conn.close()
