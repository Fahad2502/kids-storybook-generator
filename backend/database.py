"""
Database connection and query helpers.

Supports SQLite for local development and PostgreSQL for production.
Set DATABASE_URL in the environment to use PostgreSQL; otherwise SQLite is used.
"""

import json
import os
from datetime import datetime

from backend.config import DATABASE_PATH

DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras
    print("Using PostgreSQL database")
else:
    import sqlite3
    print(f"Using SQLite database: {DATABASE_PATH}")


def get_conn():
    """Return a new database connection for the configured backend."""
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return __import__("sqlite3").connect(DATABASE_PATH)


def init_database() -> None:
    """Create all tables if they do not exist and run any pending migrations."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         SERIAL PRIMARY KEY,
                    username   TEXT NOT NULL UNIQUE,
                    email      TEXT NOT NULL UNIQUE,
                    first_name TEXT NOT NULL,
                    last_name  TEXT NOT NULL,
                    password   TEXT NOT NULL,
                    date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id          SERIAL PRIMARY KEY,
                    name        TEXT    NOT NULL,
                    theme       TEXT    NOT NULL,
                    full_text   TEXT    NOT NULL,
                    is_favorite INTEGER DEFAULT 0,
                    date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating      INTEGER DEFAULT NULL,
                    user_id     INTEGER DEFAULT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_images (
                    story_id  INTEGER NOT NULL,
                    page_num  INTEGER NOT NULL,
                    image_url TEXT    NOT NULL,
                    PRIMARY KEY (story_id, page_num)
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    username   TEXT NOT NULL UNIQUE,
                    email      TEXT DEFAULT '' UNIQUE,
                    first_name TEXT DEFAULT '',
                    last_name  TEXT DEFAULT '',
                    password   TEXT NOT NULL,
                    date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    theme       TEXT    NOT NULL,
                    full_text   TEXT    NOT NULL,
                    is_favorite INTEGER DEFAULT 0,
                    date        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    rating      INTEGER DEFAULT NULL,
                    user_id     INTEGER DEFAULT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS story_images (
                    story_id  INTEGER NOT NULL,
                    page_num  INTEGER NOT NULL,
                    image_url TEXT    NOT NULL,
                    PRIMARY KEY (story_id, page_num)
                )
            """)
            # Incremental migrations for existing SQLite databases
            cur.execute("PRAGMA table_info(stories)")
            existing_columns = [row[1] for row in cur.fetchall()]
            pending_migrations = {
                "rating":  "ALTER TABLE stories ADD COLUMN rating INTEGER DEFAULT NULL",
                "user_id": "ALTER TABLE stories ADD COLUMN user_id INTEGER DEFAULT NULL",
            }
            for column, statement in pending_migrations.items():
                if column not in existing_columns:
                    cur.execute(statement)
                    print(f"Migration applied: added column '{column}'")

        conn.commit()
        print("Database ready")
    finally:
        conn.close()


def save_image_url(story_id: int, page_num: int, image_url: str) -> None:
    """Persist a generated image URL for a given story page."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO story_images (story_id, page_num, image_url) VALUES (%s, %s, %s) "
                "ON CONFLICT (story_id, page_num) DO UPDATE SET image_url = EXCLUDED.image_url",
                (story_id, page_num, image_url),
            )
        else:
            cur.execute(
                "INSERT OR REPLACE INTO story_images (story_id, page_num, image_url) VALUES (?, ?, ?)",
                (story_id, page_num, image_url),
            )
        conn.commit()
    finally:
        conn.close()


def get_image_url(story_id: int, page_num: int) -> str | None:
    """Return the cached image URL for a story page, or None if not found."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "SELECT image_url FROM story_images WHERE story_id = %s AND page_num = %s",
                (story_id, page_num),
            )
        else:
            cur.execute(
                "SELECT image_url FROM story_images WHERE story_id = ? AND page_num = ?",
                (story_id, page_num),
            )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def save_story(name: str, theme: str, story_data: dict) -> int:
    """Insert a new story record and return its generated ID."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (%s, %s, %s, %s) RETURNING id",
                (name, theme, json.dumps(story_data, default=str), datetime.now()),
            )
            story_id = cur.fetchone()[0]
        else:
            cur.execute(
                "INSERT INTO stories (name, theme, full_text, date) VALUES (?, ?, ?, ?)",
                (name, theme, json.dumps(story_data, default=str), datetime.now()),
            )
            story_id = cur.lastrowid
        conn.commit()
        return story_id
    finally:
        conn.close()


def create_user(
    username: str,
    hashed_password: str,
    email: str = "",
    first_name: str = "",
    last_name: str = "",
) -> int:
    """Insert a new user and return their ID. Raises on duplicate username or email."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "INSERT INTO users (username, email, first_name, last_name, password) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (username, email, first_name, last_name, hashed_password),
            )
            user_id = cur.fetchone()[0]
        else:
            cur.execute(
                "INSERT INTO users (username, email, first_name, last_name, password) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, first_name, last_name, hashed_password),
            )
            user_id = cur.lastrowid
        conn.commit()
        return user_id
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    """Fetch a user record by username. Returns a dict or None."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "SELECT id, username, password, first_name FROM users WHERE username = %s",
                (username,),
            )
        else:
            cur.execute(
                "SELECT id, username, password, first_name FROM users WHERE username = ?",
                (username,),
            )
        row = cur.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2], "first_name": row[3]}
        return None
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    """Fetch a user record by email address. Returns a dict or None."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute(
                "SELECT id, username, password, first_name FROM users WHERE email = %s",
                (email,),
            )
        else:
            cur.execute(
                "SELECT id, username, password, first_name FROM users WHERE email = ?",
                (email,),
            )
        row = cur.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2], "first_name": row[3]}
        return None
    finally:
        conn.close()
