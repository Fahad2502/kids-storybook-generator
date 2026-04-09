"""
migrate_db.py -- Safe database migration
Adds new columns WITHOUT deleting existing data.
Run with: venv\Scripts\python migrate_db.py
"""
import sqlite3

conn = sqlite3.connect('stories.db')
cur = conn.cursor()

# Check existing columns in users table
cur.execute("PRAGMA table_info(users)")
user_cols = [c[1] for c in cur.fetchall()]
print("Current users columns:", user_cols)

# Add missing columns to users table
migrations = {
    "email":      "ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''",
    "first_name": "ALTER TABLE users ADD COLUMN first_name TEXT DEFAULT ''",
    "last_name":  "ALTER TABLE users ADD COLUMN last_name TEXT DEFAULT ''",
}

for col, sql in migrations.items():
    if col not in user_cols:
        cur.execute(sql)
        print(f"Added column: {col}")
    else:
        print(f"Column already exists: {col}")

# Check stories table
cur.execute("PRAGMA table_info(stories)")
story_cols = [c[1] for c in cur.fetchall()]
print("Current stories columns:", story_cols)

story_migrations = {
    "rating":  "ALTER TABLE stories ADD COLUMN rating INTEGER DEFAULT NULL",
    "user_id": "ALTER TABLE stories ADD COLUMN user_id INTEGER DEFAULT NULL",
}

for col, sql in story_migrations.items():
    if col not in story_cols:
        cur.execute(sql)
        print(f"Added column: {col}")
    else:
        print(f"Column already exists: {col}")

# Create story_images table if missing
cur.execute("""
    CREATE TABLE IF NOT EXISTS story_images (
        story_id INTEGER NOT NULL,
        page_num INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        PRIMARY KEY (story_id, page_num)
    )
""")
print("story_images table: OK")

# Create users table if missing
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        username   TEXT NOT NULL UNIQUE,
        email      TEXT DEFAULT '',
        first_name TEXT DEFAULT '',
        last_name  TEXT DEFAULT '',
        password   TEXT NOT NULL,
        date       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
print("users table: OK")

conn.commit()
conn.close()

# Show final state
conn = sqlite3.connect('stories.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM stories")
print(f"\nStories preserved: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM users")
print(f"Users preserved: {cur.fetchone()[0]}")
conn.close()
print("\nMigration complete. No data was lost.")
