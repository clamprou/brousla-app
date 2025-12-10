"""Script to clear all users from the database."""
import sqlite3
from pathlib import Path

# Get the database file path
DB_DIR = Path(__file__).parent
DB_FILE = DB_DIR / "users_db.sqlite"

if not DB_FILE.exists():
    print("Database file not found. Nothing to clear.")
    exit(0)

# Connect to database
conn = sqlite3.connect(str(DB_FILE))
cursor = conn.cursor()

# Get count before deletion
cursor.execute("SELECT COUNT(*) FROM users")
count_before = cursor.fetchone()[0]

# Delete all users
cursor.execute("DELETE FROM users")
conn.commit()

# Get count after deletion
cursor.execute("SELECT COUNT(*) FROM users")
count_after = cursor.fetchone()[0]

conn.close()

print(f"Deleted {count_before} user(s) from the database.")
print(f"Remaining users: {count_after}")

