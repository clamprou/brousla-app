"""Database module for SQLite user storage."""
import json
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

# Get the directory where this file is located
_DB_DIR = Path(__file__).parent.parent
_DB_FILE = _DB_DIR / "users_db.sqlite"
_JSON_FILE = _DB_DIR / "users_db.json"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(str(_DB_FILE))
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize database and create tables if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add email verification columns if they don't exist (migration)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token_expires TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_confirmation_email_sent TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Set email_verified=1 for existing users (grandfather them)
        # Only update users where email_verified IS NULL (existed before migration)
        # Don't update users with email_verified=0 (new unverified users)
        cursor.execute("""
            UPDATE users 
            SET email_verified = 1 
            WHERE email_verified IS NULL
        """)
        
        # Create index on email for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        
        # Create index on verification token for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token)
        """)
        
        conn.commit()


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified, 
                   email_verification_token, email_verification_token_expires,
                   last_confirmation_email_sent
            FROM users WHERE email = ?
        """, (email,))
        row = cursor.fetchone()
        
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"]
            }
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified,
                   email_verification_token, email_verification_token_expires,
                   last_confirmation_email_sent
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"]
            }
        return None


def create_user(user_id: str, email: str, hashed_password: str, 
                email_verified: bool = False, 
                email_verification_token: Optional[str] = None,
                email_verification_token_expires: Optional[str] = None) -> None:
    """Create a new user in the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (id, email, hashed_password, email_verified, 
               email_verification_token, email_verification_token_expires) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, email, hashed_password, 1 if email_verified else 0, 
             email_verification_token, email_verification_token_expires)
        )
        conn.commit()


def update_user_email_verified(user_id: str, verified: bool) -> None:
    """Update user's email verification status."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET email_verified = ? WHERE id = ?",
            (1 if verified else 0, user_id)
        )
        conn.commit()


def get_user_by_verification_token(token: str) -> Optional[dict]:
    """Get user by email verification token."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified,
                   email_verification_token, email_verification_token_expires,
                   last_confirmation_email_sent
            FROM users WHERE email_verification_token = ?
        """, (token,))
        row = cursor.fetchone()
        
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"]
            }
        return None


def update_user_verification_token(user_id: str, token: Optional[str], expires_at: Optional[str]) -> None:
    """Update user's email verification token."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE users SET email_verification_token = ?, 
               email_verification_token_expires = ? WHERE id = ?""",
            (token, expires_at, user_id)
        )
        conn.commit()


def update_user_last_confirmation_email_sent(user_id: str, timestamp: str) -> None:
    """Update the timestamp when confirmation email was last sent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_confirmation_email_sent = ? WHERE id = ?",
            (timestamp, user_id)
        )
        conn.commit()


def get_user_last_confirmation_email_sent(user_id: str) -> Optional[str]:
    """Get the timestamp when confirmation email was last sent."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_confirmation_email_sent FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            return row["last_confirmation_email_sent"]
        return None


def migrate_from_json(json_file_path: Path) -> None:
    """Migrate existing JSON data to SQLite database."""
    if not json_file_path.exists():
        return
    
    print(f"Migrating users from {json_file_path} to SQLite database...")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        if not users_data:
            print("No users found in JSON file to migrate.")
            return
        
        migrated_count = 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for email, user_data in users_data.items():
                try:
                    # Check if user already exists
                    existing = get_user_by_email(email)
                    if existing:
                        print(f"User {email} already exists in database, skipping...")
                        continue
                    
                    # Insert user
                    cursor.execute(
                        "INSERT INTO users (id, email, hashed_password) VALUES (?, ?, ?)",
                        (user_data["id"], user_data["email"], user_data["hashed_password"])
                    )
                    migrated_count += 1
                except sqlite3.IntegrityError as e:
                    print(f"Error migrating user {email}: {e}")
                    continue
            
            conn.commit()
        
        print(f"Successfully migrated {migrated_count} user(s) from JSON to SQLite.")
        
    except (json.JSONDecodeError, IOError, KeyError) as e:
        print(f"Warning: Failed to migrate users from JSON: {e}")


# Initialize database on module import
init_db()

# Migrate existing JSON data if it exists
if _JSON_FILE.exists():
    migrate_from_json(_JSON_FILE)

