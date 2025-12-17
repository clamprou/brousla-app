"""Database module for SQLite user storage."""
import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

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
                hashed_password TEXT,
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
        
        # Add subscription columns if they don't exist (migration)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_plan TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN trial_executions_used INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_start_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_end_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN executions_used_this_month INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN executions_reset_date TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN monthly_workflow_limit INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Grandfather existing users: set trial_executions_used = 0 for all existing users
        # Only update users where trial_executions_used IS NULL (newly added column)
        cursor.execute("""
            UPDATE users 
            SET trial_executions_used = 0 
            WHERE trial_executions_used IS NULL
        """)
        
        # Migration: Allow NULL passwords for OAuth users
        # SQLite doesn't support ALTER COLUMN, so we need to check and migrate if needed
        try:
            # Check the current schema of the hashed_password column
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            hashed_password_info = None
            for col in columns:
                if col[1] == 'hashed_password':  # Column name is at index 1
                    hashed_password_info = col
                    break
            
            # If the column exists and has NOT NULL constraint (notnull=1), we need to migrate
            if hashed_password_info and hashed_password_info[3] == 1:  # notnull is at index 3
                print("Migrating users table to allow NULL passwords for OAuth users...")
                # Create new table with NULL allowed
                cursor.execute("""
                    CREATE TABLE users_new (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        hashed_password TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        email_verified INTEGER DEFAULT 0,
                        email_verification_token TEXT,
                        email_verification_token_expires TIMESTAMP,
                        last_confirmation_email_sent TIMESTAMP
                    )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                    INSERT INTO users_new 
                    (id, email, hashed_password, created_at, email_verified, 
                     email_verification_token, email_verification_token_expires, 
                     last_confirmation_email_sent)
                    SELECT id, email, hashed_password, created_at, email_verified,
                           email_verification_token, email_verification_token_expires,
                           last_confirmation_email_sent
                    FROM users
                """)
                
                # Drop old table
                cursor.execute("DROP TABLE users")
                
                # Rename new table
                cursor.execute("ALTER TABLE users_new RENAME TO users")
                
                # Recreate indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token)
                """)
                
                conn.commit()
                print("Migration completed successfully.")
        except sqlite3.OperationalError as e:
            # If migration fails, log but don't crash (table might already be migrated)
            print(f"Migration check completed (table may already be migrated): {e}")
            pass
        
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
                   last_confirmation_email_sent,
                   subscription_plan, subscription_status, trial_executions_used,
                   subscription_start_date, subscription_end_date,
                   executions_used_this_month, executions_reset_date,
                   stripe_customer_id, stripe_subscription_id, monthly_workflow_limit
            FROM users WHERE email = ?
        """, (email,))
        row = cursor.fetchone()
        
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],  # Can be None for OAuth users
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"],
                "subscription_plan": row["subscription_plan"],
                "subscription_status": row["subscription_status"],
                "trial_executions_used": row["trial_executions_used"] or 0,
                "subscription_start_date": row["subscription_start_date"],
                "subscription_end_date": row["subscription_end_date"],
                "executions_used_this_month": row["executions_used_this_month"] or 0,
                "executions_reset_date": row["executions_reset_date"],
                "stripe_customer_id": row["stripe_customer_id"],
                "stripe_subscription_id": row["stripe_subscription_id"]
            }
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified,
                   email_verification_token, email_verification_token_expires,
                   last_confirmation_email_sent,
                   subscription_plan, subscription_status, trial_executions_used,
                   subscription_start_date, subscription_end_date,
                   executions_used_this_month, executions_reset_date,
                   stripe_customer_id, stripe_subscription_id, monthly_workflow_limit
            FROM users WHERE id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            # sqlite3.Row doesn't support .get(), use direct access
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],  # Can be None for OAuth users
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"],
                "subscription_plan": row["subscription_plan"],
                "subscription_status": row["subscription_status"],
                "trial_executions_used": row["trial_executions_used"] or 0,
                "subscription_start_date": row["subscription_start_date"],
                "subscription_end_date": row["subscription_end_date"],
                "executions_used_this_month": row["executions_used_this_month"] or 0,
                "executions_reset_date": row["executions_reset_date"],
                "stripe_customer_id": row["stripe_customer_id"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "monthly_workflow_limit": row["monthly_workflow_limit"]
            }
        return None


def create_user(user_id: str, email: str, hashed_password: Optional[str] = None, 
                email_verified: bool = False, 
                email_verification_token: Optional[str] = None,
                email_verification_token_expires: Optional[str] = None) -> None:
    """Create a new user in the database.
    
    Args:
        user_id: Unique user identifier
        email: User email address
        hashed_password: Hashed password (None for OAuth users)
        email_verified: Whether email is verified (default True for OAuth users)
        email_verification_token: Email verification token
        email_verification_token_expires: Token expiration timestamp
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (id, email, hashed_password, email_verified, 
               email_verification_token, email_verification_token_expires,
               subscription_plan, trial_executions_used) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, email, hashed_password, 1 if email_verified else 0, 
             email_verification_token, email_verification_token_expires,
             'trial', 0)
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
                "hashed_password": row["hashed_password"],  # Can be None for OAuth users
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


def get_user_subscription(user_id: str) -> Optional[dict]:
    """Get user subscription details."""
    user = get_user_by_id(user_id)
    if not user:
        return None
    
    return {
        "subscription_plan": user.get("subscription_plan"),
        "subscription_status": user.get("subscription_status"),
        "trial_executions_used": user.get("trial_executions_used", 0),
        "subscription_start_date": user.get("subscription_start_date"),
        "subscription_end_date": user.get("subscription_end_date"),
        "executions_used_this_month": user.get("executions_used_this_month", 0),
        "executions_reset_date": user.get("executions_reset_date"),
        "stripe_customer_id": user.get("stripe_customer_id"),
        "stripe_subscription_id": user.get("stripe_subscription_id"),
        "monthly_workflow_limit": user.get("monthly_workflow_limit")
    }


def increment_user_execution_count(user_id: str) -> None:
    """Increment execution count for user (trial or monthly)."""
    from datetime import datetime, timedelta
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = get_user_by_id(user_id)
        
        if not user:
            return
        
        subscription_plan = user.get("subscription_plan")
        
        if subscription_plan == "trial":
            # Increment trial executions
            cursor.execute("""
                UPDATE users 
                SET trial_executions_used = COALESCE(trial_executions_used, 0) + 1
                WHERE id = ?
            """, (user_id,))
        elif subscription_plan in ("basic", "plus", "pro"):
            # Check if we need to reset monthly counter
            reset_date = user.get("executions_reset_date")
            now = datetime.utcnow()
            
            if not reset_date:
                # First execution, set reset date to now
                reset_date = now
                cursor.execute("""
                    UPDATE users 
                    SET executions_used_this_month = 1,
                        executions_reset_date = ?
                    WHERE id = ?
                """, (reset_date.isoformat(), user_id))
            else:
                # Parse reset date and check if we need to reset
                try:
                    reset_dt = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
                    if reset_dt.tzinfo:
                        reset_dt = reset_dt.replace(tzinfo=None)
                    
                    # If reset date is in the past, reset counter
                    if reset_dt < now:
                        # Calculate next month's reset date
                        if reset_dt.month == 12:
                            next_reset = reset_dt.replace(year=reset_dt.year + 1, month=1, day=1)
                        else:
                            next_reset = reset_dt.replace(month=reset_dt.month + 1, day=1)
                        
                        cursor.execute("""
                            UPDATE users 
                            SET executions_used_this_month = 1,
                                executions_reset_date = ?
                            WHERE id = ?
                        """, (next_reset.isoformat(), user_id))
                    else:
                        # Just increment counter
                        cursor.execute("""
                            UPDATE users 
                            SET executions_used_this_month = COALESCE(executions_used_this_month, 0) + 1
                            WHERE id = ?
                        """, (user_id,))
                except (ValueError, AttributeError):
                    # Invalid date format, reset to now
                    cursor.execute("""
                        UPDATE users 
                        SET executions_used_this_month = 1,
                            executions_reset_date = ?
                        WHERE id = ?
                    """, (now.isoformat(), user_id))
        
        conn.commit()


def check_user_can_execute(user_id: str) -> tuple[bool, str]:
    """
    Check if user can execute workflows.
    
    Returns:
        (can_execute: bool, message: str)
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, "User not found"
    
    subscription_plan = user.get("subscription_plan")
    subscription_status = user.get("subscription_status")
    
    # Check if subscription is active
    if subscription_plan in ("basic", "plus", "pro"):
        if subscription_status != "active":
            return False, "Subscription is not active. Please renew your subscription."
        
        # Check subscription end date
        end_date = user.get("subscription_end_date")
        if end_date:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=None)
                now = datetime.utcnow()
                if end_dt < now:
                    return False, "Subscription has expired. Please renew your subscription."
            except (ValueError, AttributeError):
                pass  # Invalid date, continue check
    
    # Check trial limit
    if subscription_plan == "trial" or subscription_plan is None:
        trial_used = user.get("trial_executions_used", 0)
        if trial_used >= 5:
            return False, "Free trial limit reached. Please upgrade to continue using AI workflows."
    
    # Check plan limits using monthly_workflow_limit from Stripe metadata
    if subscription_plan in ("basic", "plus", "pro"):
        monthly_limit = user.get("monthly_workflow_limit")
        if monthly_limit is not None:
            executions_used = user.get("executions_used_this_month", 0)
            if executions_used >= monthly_limit:
                return False, f"Monthly execution limit reached ({executions_used}/{monthly_limit}). Please upgrade your plan for more executions."
        else:
            # Fallback to default limits if metadata not set (shouldn't happen in production)
            logger.warning(f"User {user_id} has subscription plan {subscription_plan} but no monthly_workflow_limit set")
            if subscription_plan == "basic":
                monthly_limit = 500
            elif subscription_plan == "plus":
                monthly_limit = 2000
            elif subscription_plan == "pro":
                monthly_limit = 5000
            else:
                monthly_limit = 0
            
            executions_used = user.get("executions_used_this_month", 0)
            if executions_used >= monthly_limit:
                return False, f"Monthly execution limit reached ({executions_used}/{monthly_limit}). Please upgrade your plan for more executions."
    
    return True, "OK"


def update_user_subscription(
    user_id: str,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    monthly_workflow_limit: Optional[int] = None
) -> None:
    """Update user subscription information."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if plan is not None:
            updates.append("subscription_plan = ?")
            params.append(plan)
        
        if status is not None:
            updates.append("subscription_status = ?")
            params.append(status)
        
        if stripe_customer_id is not None:
            updates.append("stripe_customer_id = ?")
            params.append(stripe_customer_id)
        
        if stripe_subscription_id is not None:
            updates.append("stripe_subscription_id = ?")
            params.append(stripe_subscription_id)
        
        if start_date is not None:
            updates.append("subscription_start_date = ?")
            params.append(start_date)
        
        if end_date is not None:
            updates.append("subscription_end_date = ?")
            params.append(end_date)
        
        if monthly_workflow_limit is not None:
            updates.append("monthly_workflow_limit = ?")
            params.append(monthly_workflow_limit)
        
        if updates:
            params.append(user_id)
            cursor.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()


def get_user_by_stripe_subscription_id(stripe_subscription_id: str) -> Optional[dict]:
    """Get user by Stripe subscription ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified,
                   email_verification_token, email_verification_token_expires,
                   last_confirmation_email_sent,
                   subscription_plan, subscription_status, trial_executions_used,
                   subscription_start_date, subscription_end_date,
                   executions_used_this_month, executions_reset_date,
                   stripe_customer_id, stripe_subscription_id, monthly_workflow_limit
            FROM users WHERE stripe_subscription_id = ?
        """, (stripe_subscription_id,))
        row = cursor.fetchone()
        
        if row:
            email_verified_val = row["email_verified"]
            return {
                "id": row["id"],
                "email": row["email"],
                "hashed_password": row["hashed_password"],
                "email_verified": bool(email_verified_val) if email_verified_val is not None else True,
                "email_verification_token": row["email_verification_token"],
                "email_verification_token_expires": row["email_verification_token_expires"],
                "last_confirmation_email_sent": row["last_confirmation_email_sent"],
                "subscription_plan": row["subscription_plan"],
                "subscription_status": row["subscription_status"],
                "trial_executions_used": row["trial_executions_used"] or 0,
                "subscription_start_date": row["subscription_start_date"],
                "subscription_end_date": row["subscription_end_date"],
                "executions_used_this_month": row["executions_used_this_month"] or 0,
                "executions_reset_date": row["executions_reset_date"],
                "stripe_customer_id": row["stripe_customer_id"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "monthly_workflow_limit": row["monthly_workflow_limit"]
            }
        return None


def reset_monthly_executions(user_id: str) -> None:
    """Reset monthly execution counter (called on billing cycle reset)."""
    from datetime import datetime
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.utcnow()
        
        # Calculate next month's reset date
        if now.month == 12:
            next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        cursor.execute("""
            UPDATE users 
            SET executions_used_this_month = 0,
                executions_reset_date = ?
            WHERE id = ?
        """, (next_reset.isoformat(), user_id))
        conn.commit()


# Initialize database on module import
init_db()

# Migrate existing JSON data if it exists
if _JSON_FILE.exists():
    migrate_from_json(_JSON_FILE)

