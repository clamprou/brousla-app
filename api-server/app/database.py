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
        
        # Create users table (clean schema - only essential columns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT,
                email_verified INTEGER DEFAULT 0,
                email_verification_token TEXT,
                email_verification_token_expires TIMESTAMP
            )
        """)
        
        # Migrate existing table if it has old columns
        _migrate_users_table_to_clean_schema(cursor)
        
        # Create usage table (tracks execution counts for all users)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                trial_workflows_used INTEGER DEFAULT 0,
                monthly_workflows_used INTEGER DEFAULT 0,
                last_reset_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Create index on user_id for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_user_id ON usage(user_id)
        """)
        
        # Create subscriptions table (mirrors Stripe subscription data only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                stripe_price_id TEXT,
                plan TEXT,
                status TEXT,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                cancel_at_period_end INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)
        
        # Create index on user_id for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)
        """)
        
        # Create index on stripe_subscription_id for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id)
        """)
        
        # Migrate existing subscription data to new schema
        _migrate_subscriptions_to_new_schema(cursor)
        
        # Create index on email for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        
        # Create index on verification token for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(email_verification_token)
        """)
        
        conn.commit()


def _migrate_users_table_to_clean_schema(cursor) -> None:
    """Migrate users table to clean schema (remove unnecessary columns)."""
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        column_names = {col[1] for col in columns}
        
        # Check if migration needed (old schema has created_at or last_confirmation_email_sent)
        has_old_columns = 'created_at' in column_names or 'last_confirmation_email_sent' in column_names
        
        if not has_old_columns:
            # Already clean, just ensure email_verified exists
            if 'email_verified' not in column_names:
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
            if 'email_verification_token' not in column_names:
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token TEXT")
                except sqlite3.OperationalError:
                    pass
            if 'email_verification_token_expires' not in column_names:
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token_expires TIMESTAMP")
                except sqlite3.OperationalError:
                    pass
            return
        
        logger.info("Migrating users table to clean schema...")
        
        # Create new clean table
        cursor.execute("""
            CREATE TABLE users_new (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT,
                email_verified INTEGER DEFAULT 0,
                email_verification_token TEXT,
                email_verification_token_expires TIMESTAMP
            )
        """)
        
        # Copy data from old table (only essential columns)
        cursor.execute("""
            INSERT INTO users_new 
            (id, email, hashed_password, email_verified, 
             email_verification_token, email_verification_token_expires)
            SELECT 
                id, 
                email, 
                hashed_password,
                COALESCE(email_verified, 0),
                email_verification_token,
                email_verification_token_expires
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
        
        logger.info("Successfully migrated users table to clean schema")
        
    except sqlite3.OperationalError as e:
        logger.debug(f"Users table migration check: {e}")


def _migrate_subscriptions_to_new_schema(cursor) -> None:
    """Migrate subscriptions table to new schema (separate usage from subscriptions)."""
    try:
        # Check if old subscriptions table exists with old schema
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = cursor.fetchall()
        column_names = {col[1] for col in columns}
        
        # Check if migration already done (new schema has stripe_price_id, old doesn't)
        has_new_schema = 'stripe_price_id' in column_names
        has_old_schema = 'trial_executions_used' in column_names or 'executions_used_this_month' in column_names
        
        if has_new_schema and not has_old_schema:
            # Already migrated
            # Ensure all users have usage records
            cursor.execute("""
                INSERT OR IGNORE INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
                SELECT id, 0, 0
                FROM users
                WHERE id NOT IN (SELECT user_id FROM usage)
            """)
            return
        
        if not has_old_schema:
            # No old schema to migrate from
            # Just ensure all users have usage records
            cursor.execute("""
                INSERT OR IGNORE INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
                SELECT id, 0, 0
                FROM users
                WHERE id NOT IN (SELECT user_id FROM usage)
            """)
            return
        
        logger.info("Migrating subscriptions table to new schema...")
        
        # Step 1: Migrate usage data to usage table
        cursor.execute("""
            INSERT OR IGNORE INTO usage (
                user_id, trial_workflows_used, monthly_workflows_used, last_reset_date
            )
            SELECT 
                user_id,
                COALESCE(trial_executions_used, 0),
                COALESCE(executions_used_this_month, 0),
                executions_reset_date
            FROM subscriptions
            WHERE user_id IS NOT NULL
        """)
        
        # Step 2: Create new subscriptions table with cleaned schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                stripe_subscription_id TEXT UNIQUE NOT NULL,
                stripe_price_id TEXT,
                plan TEXT,
                status TEXT,
                current_period_start TIMESTAMP,
                current_period_end TIMESTAMP,
                cancel_at_period_end INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id)
            )
        """)
        
        # Step 3: Copy subscription data (only Stripe-related fields)
        # Only copy rows that have stripe_subscription_id (paid subscriptions)
        cursor.execute("""
            INSERT INTO subscriptions_new (
                user_id, stripe_subscription_id, stripe_price_id, plan, status,
                current_period_start, current_period_end, cancel_at_period_end,
                created_at, updated_at
            )
            SELECT 
                user_id,
                stripe_subscription_id,
                NULL as stripe_price_id,  -- Will be populated from Stripe API if needed
                plan,
                status,
                subscription_start_date as current_period_start,
                subscription_end_date as current_period_end,
                0 as cancel_at_period_end,  -- Default, will be updated by webhooks
                created_at,
                updated_at
            FROM subscriptions
            WHERE stripe_subscription_id IS NOT NULL
        """)
        
        # Step 4: Drop old table and rename new one
        cursor.execute("DROP TABLE subscriptions")
        cursor.execute("ALTER TABLE subscriptions_new RENAME TO subscriptions")
        
        # Step 5: Recreate indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_subscription_id ON subscriptions(stripe_subscription_id)
        """)
        
        # Step 6: Create usage records for users without subscriptions (trial users)
        cursor.execute("""
            INSERT OR IGNORE INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
            SELECT id, 0, 0
            FROM users
            WHERE id NOT IN (SELECT user_id FROM usage)
        """)
        
        logger.info("Successfully migrated subscriptions table to new schema")
        
    except sqlite3.OperationalError as e:
        # Migration might have already been done or table doesn't exist
        logger.debug(f"Subscription migration check: {e}")
        # Ensure all users have usage records even if migration failed
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
                SELECT id, 0, 0
                FROM users
                WHERE id NOT IN (SELECT user_id FROM usage)
            """)
        except sqlite3.OperationalError:
            pass


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified, 
                   email_verification_token, email_verification_token_expires
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
                "email_verification_token_expires": row["email_verification_token_expires"]
            }
        return None


def get_user_by_id(user_id: str) -> Optional[dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, hashed_password, email_verified,
                   email_verification_token, email_verification_token_expires
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
                "email_verification_token_expires": row["email_verification_token_expires"]
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
               email_verification_token, email_verification_token_expires) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, email, hashed_password, 1 if email_verified else 0, 
             email_verification_token, email_verification_token_expires)
        )
        
        # Create usage record for new user (trial users have no subscription row)
        cursor.execute("""
            INSERT INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
            VALUES (?, 0, 0)
        """, (user_id,))
        
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
                   email_verification_token, email_verification_token_expires
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
                "email_verification_token_expires": row["email_verification_token_expires"]
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


def get_user_usage(user_id: str) -> Optional[dict]:
    """Get user usage details."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT trial_workflows_used, monthly_workflows_used, last_reset_date
            FROM usage WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "trial_workflows_used": row["trial_workflows_used"] or 0,
                "monthly_workflows_used": row["monthly_workflows_used"] or 0,
                "last_reset_date": row["last_reset_date"]
            }
        
        # Create usage record if doesn't exist (shouldn't happen, but safety check)
        cursor.execute("""
            INSERT INTO usage (user_id, trial_workflows_used, monthly_workflows_used)
            VALUES (?, 0, 0)
        """, (user_id,))
        conn.commit()
        
        return {
            "trial_workflows_used": 0,
            "monthly_workflows_used": 0,
            "last_reset_date": None
        }


def get_monthly_workflow_limit_from_stripe(stripe_price_id: Optional[str]) -> Optional[int]:
    """Fetch monthly workflow limit from Stripe price metadata."""
    if not stripe_price_id:
        return None
    
    try:
        import stripe
        from app.config import settings
        import os
        
        stripe.api_key = settings.stripe_secret_key or os.getenv("STRIPE_SECRET_KEY", "")
        if not stripe.api_key:
            logger.warning("Stripe API key not configured, cannot fetch monthly limit")
            return None
        
        price = stripe.Price.retrieve(stripe_price_id)
        price_metadata = price.get("metadata", {})
        monthly_workflow_limit_str = price_metadata.get("monthly_workflow_limit")
        
        if monthly_workflow_limit_str:
            try:
                return int(monthly_workflow_limit_str)
            except (ValueError, TypeError):
                logger.warning(f"Invalid monthly_workflow_limit in price metadata: {monthly_workflow_limit_str}")
                return None
    except Exception as e:
        logger.warning(f"Error fetching monthly limit from Stripe for price {stripe_price_id}: {e}")
        return None
    
    return None


def get_user_subscription(user_id: str) -> Optional[dict]:
    """Get user subscription details (only Stripe subscription data, no usage)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT plan, status, stripe_subscription_id, stripe_price_id,
                   current_period_start, current_period_end, cancel_at_period_end
            FROM subscriptions WHERE user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        
        if row:
            return {
                "subscription_plan": row["plan"],
                "subscription_status": row["status"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "stripe_price_id": row["stripe_price_id"],
                "current_period_start": row["current_period_start"],
                "current_period_end": row["current_period_end"],
                "cancel_at_period_end": bool(row["cancel_at_period_end"]) if row["cancel_at_period_end"] is not None else False
            }
        
        # No subscription (trial user)
        return None


def increment_user_execution_count(user_id: str) -> None:
    """Increment execution count for user (trial or monthly)."""
    from datetime import datetime
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get subscription to determine if trial or paid
        subscription = get_user_subscription(user_id)
        
        # Get usage record
        usage = get_user_usage(user_id)
        if not usage:
            return
        
        def _first_day_next_month(dt: datetime) -> datetime:
            """Return UTC timestamp for next month's 1st day at 00:00:00."""
            if dt.month == 12:
                return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # If no subscription, user is on trial
        if not subscription:
            # Increment trial executions
            current_trial_used = usage.get("trial_workflows_used", 0)
            new_trial_used = current_trial_used + 1
            
            cursor.execute("""
                UPDATE usage 
                SET trial_workflows_used = trial_workflows_used + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            
            # If trial limit is reached (5 executions), deactivate all workflows
            if new_trial_used >= 5:
                _deactivate_all_user_workflows(user_id)
        else:
            # Paid subscription - increment monthly counter
            subscription_plan = subscription.get("subscription_plan")
            if subscription_plan in ("basic", "plus", "pro"):
                # last_reset_date stores the *next* time we reset the monthly counter (UTC).
                reset_date = usage.get("last_reset_date")
                now = datetime.utcnow()
                
                if not reset_date:
                    # First execution: set next reset date to start of next month.
                    next_reset = _first_day_next_month(now)
                    cursor.execute("""
                        UPDATE usage 
                        SET monthly_workflows_used = 1,
                            last_reset_date = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (next_reset.isoformat(), user_id))
                else:
                    # Parse next reset date and check if we need to reset
                    try:
                        reset_dt = datetime.fromisoformat(reset_date.replace('Z', '+00:00'))
                        if reset_dt.tzinfo:
                            reset_dt = reset_dt.replace(tzinfo=None)
                        
                        # If we've passed the next reset timestamp, reset counter and set a new future reset.
                        if reset_dt <= now:
                            next_reset = _first_day_next_month(now)
                            cursor.execute("""
                                UPDATE usage 
                                SET monthly_workflows_used = 1,
                                    last_reset_date = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            """, (next_reset.isoformat(), user_id))
                        else:
                            # Just increment counter
                            cursor.execute("""
                                UPDATE usage 
                                SET monthly_workflows_used = monthly_workflows_used + 1,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE user_id = ?
                            """, (user_id,))
                    except (ValueError, AttributeError):
                        # Invalid date format, reset counter and set next reset date to start of next month.
                        next_reset = _first_day_next_month(now)
                        cursor.execute("""
                            UPDATE usage 
                            SET monthly_workflows_used = 1,
                                last_reset_date = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?
                        """, (next_reset.isoformat(), user_id))
        
        conn.commit()


def _deactivate_all_user_workflows(user_id: str) -> None:
    """
    Deactivate all active workflows for a user when trial limit is reached.
    Calls the workflow server's deactivate-all endpoint.
    """
    import httpx
    
    try:
        # Workflow server runs on port 8000
        workflow_server_url = "http://127.0.0.1:8000"
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{workflow_server_url}/workflows/deactivate-all",
                headers={"X-User-Id": user_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logger.info(f"Deactivated {result.get('count', 0)} workflow(s) for user {user_id} (trial limit reached)")
                else:
                    logger.warning(f"Failed to deactivate workflows for user {user_id}: {result.get('error', 'Unknown error')}")
            else:
                logger.warning(f"Workflow server returned error {response.status_code} when deactivating workflows for user {user_id}")
    except httpx.RequestError as e:
        # Don't fail the execution count increment if workflow deactivation fails
        # This is a best-effort operation
        logger.warning(f"Could not deactivate workflows for user {user_id} (workflow server may be unavailable): {str(e)}")
    except Exception as e:
        logger.warning(f"Unexpected error deactivating workflows for user {user_id}: {str(e)}")


def check_user_can_execute(user_id: str) -> tuple[bool, str]:
    """
    Check if user can execute workflows.
    
    Returns:
        (can_execute: bool, message: str)
    """
    user = get_user_by_id(user_id)
    if not user:
        return False, "User not found"
    
    subscription = get_user_subscription(user_id)
    usage = get_user_usage(user_id)
    
    if not usage:
        return False, "Usage record not found"
    
    # If no subscription, user is on trial
    if not subscription:
        trial_used = usage.get("trial_workflows_used", 0)
        if trial_used >= 5:
            return False, "Free trial limit reached. Please upgrade to continue using AI workflows."
        return True, "OK"
    
    # Paid subscription - check status and limits
    subscription_plan = subscription.get("subscription_plan")
    subscription_status = subscription.get("subscription_status")
    cancel_at_period_end = subscription.get("cancel_at_period_end") or False
    
    # Check if subscription is active
    if subscription_plan in ("basic", "plus", "pro"):
        # Check subscription end date first (if present), so we can give a precise expiry message.
        end_date = subscription.get("current_period_end")
        now = None
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

        # Stripe statuses like "past_due" can still be within a paid/grace period.
        allowed_statuses = {"active", "past_due"}
        if subscription_status not in allowed_statuses:
            # If the user explicitly cancelled at period end, keep access until period end.
            if subscription_status == "cancelled" and cancel_at_period_end and end_date:
                # end_date already checked above; if it's not expired, allow.
                pass
            else:
                return False, "Subscription is not active. Please renew your subscription."
        
        # Check monthly limit - fetch from Stripe
        stripe_price_id = subscription.get("stripe_price_id")
        monthly_limit = get_monthly_workflow_limit_from_stripe(stripe_price_id)
        
        if monthly_limit is not None:
            executions_used = usage.get("monthly_workflows_used", 0)
            if executions_used >= monthly_limit:
                return False, f"Monthly execution limit reached ({executions_used}/{monthly_limit}). Please upgrade your plan for more executions."
        else:
            # Fallback to default limits if metadata not set (shouldn't happen in production)
            logger.warning(f"User {user_id} has subscription plan {subscription_plan} but could not fetch monthly_workflow_limit from Stripe")
            if subscription_plan == "basic":
                monthly_limit = 500
            elif subscription_plan == "plus":
                monthly_limit = 2000
            elif subscription_plan == "pro":
                monthly_limit = 5000
            else:
                monthly_limit = 0
            
            executions_used = usage.get("monthly_workflows_used", 0)
            if executions_used >= monthly_limit:
                return False, f"Monthly execution limit reached ({executions_used}/{monthly_limit}). Please upgrade your plan for more executions."
    
    return True, "OK"


def update_user_subscription(
    user_id: str,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    stripe_price_id: Optional[str] = None,
    current_period_start: Optional[str] = None,
    current_period_end: Optional[str] = None,
    cancel_at_period_end: Optional[bool] = None
) -> None:
    """Update user subscription information (Stripe mirror only, no usage fields)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if subscription exists
        cursor.execute("SELECT user_id FROM subscriptions WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()
        
        if not exists:
            # Subscription must have stripe_subscription_id
            if not stripe_subscription_id:
                logger.warning(f"Cannot create subscription for user {user_id} without stripe_subscription_id")
                return
            
            # Create subscription if it doesn't exist
            cursor.execute("""
                INSERT INTO subscriptions (
                    user_id,
                    stripe_subscription_id,
                    stripe_price_id,
                    plan,
                    status,
                    current_period_start,
                    current_period_end,
                    cancel_at_period_end
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                stripe_subscription_id,
                stripe_price_id,
                plan,
                status,
                current_period_start,
                current_period_end,
                1 if cancel_at_period_end else 0
            ))
            conn.commit()
            return
        
        updates = []
        params = []
        
        if plan is not None:
            updates.append("plan = ?")
            params.append(plan)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if stripe_subscription_id is not None:
            updates.append("stripe_subscription_id = ?")
            params.append(stripe_subscription_id)
        
        if stripe_price_id is not None:
            updates.append("stripe_price_id = ?")
            params.append(stripe_price_id)
        
        if current_period_start is not None:
            updates.append("current_period_start = ?")
            params.append(current_period_start)
        
        if current_period_end is not None:
            updates.append("current_period_end = ?")
            params.append(current_period_end)
        
        if cancel_at_period_end is not None:
            updates.append("cancel_at_period_end = ?")
            params.append(1 if cancel_at_period_end else 0)
        
        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            cursor.execute(
                f"UPDATE subscriptions SET {', '.join(updates)} WHERE user_id = ?",
                params
            )
            conn.commit()


def get_user_by_stripe_subscription_id(stripe_subscription_id: str) -> Optional[dict]:
    """Get user by Stripe subscription ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.hashed_password, u.email_verified,
                   u.email_verification_token, u.email_verification_token_expires,
                   s.plan as subscription_plan, s.status as subscription_status, 
                   s.stripe_subscription_id, s.stripe_price_id,
                   s.current_period_start, s.current_period_end, s.cancel_at_period_end
            FROM users u
            INNER JOIN subscriptions s ON u.id = s.user_id
            WHERE s.stripe_subscription_id = ?
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
                "subscription_plan": row["subscription_plan"],
                "subscription_status": row["subscription_status"],
                "stripe_subscription_id": row["stripe_subscription_id"],
                "stripe_price_id": row["stripe_price_id"],
                "current_period_start": row["current_period_start"],
                "current_period_end": row["current_period_end"],
                "cancel_at_period_end": bool(row["cancel_at_period_end"]) if row["cancel_at_period_end"] is not None else False
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
            UPDATE usage 
            SET monthly_workflows_used = 0,
                last_reset_date = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (next_reset.isoformat(), user_id))
        conn.commit()


# Initialize database on module import
init_db()

# Migrate existing JSON data if it exists
if _JSON_FILE.exists():
    migrate_from_json(_JSON_FILE)

