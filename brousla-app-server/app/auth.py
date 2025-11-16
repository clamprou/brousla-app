"""Authentication utilities: JWT, password hashing, and auth dependencies."""
import base64
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

# JWT token bearer scheme
security = HTTPBearer()

# Get the directory where this file is located
_AUTH_DIR = Path(__file__).parent
_USERS_DB_FILE = _AUTH_DIR.parent / "users_db.json"


def load_users_db() -> dict:
    """Load users database from JSON file."""
    if _USERS_DB_FILE.exists():
        try:
            with open(_USERS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load users database: {e}. Starting with empty database.")
            return {}
    return {}


def save_users_db(users: dict) -> None:
    """Save users database to JSON file."""
    try:
        with open(_USERS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error: Failed to save users database: {e}")


# Persistent user store (loaded from JSON file on startup)
# Format: {email: {"id": str, "email": str, "hashed_password": str}}
users_db: dict = load_users_db()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Note: bcrypt has a 72-byte limit. Passwords longer than 72 bytes
    will be pre-hashed with SHA256 before bcrypt hashing for security.
    """
    password_bytes = password.encode('utf-8')
    
    # If password exceeds bcrypt's 72-byte limit, pre-hash with SHA256
    # This ensures we can handle long passwords securely
    if len(password_bytes) > 72:
        # Pre-hash with SHA256 (produces 32-byte binary)
        password_hash_bytes = hashlib.sha256(password_bytes).digest()
        # Convert to base64 to get a compact string representation (44 chars = 44 bytes)
        password_hash_b64 = base64.b64encode(password_hash_bytes).decode('utf-8')
        # Use the base64 hash as the password for bcrypt
        password_to_hash = password_hash_b64
    else:
        password_to_hash = password
    
    # Ensure the final password is not longer than 72 bytes when encoded
    final_bytes = password_to_hash.encode('utf-8')
    if len(final_bytes) > 72:
        # Truncate to 72 bytes
        password_to_hash = password_to_hash[:72]
    
    # Hash using bcrypt directly (avoiding passlib's initialization issues)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_to_hash.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    password_bytes = plain_password.encode('utf-8')
    
    # Apply the same transformation as hash_password
    if len(password_bytes) > 72:
        # Pre-hash with SHA256 to match the hashing process
        password_hash_bytes = hashlib.sha256(password_bytes).digest()
        # Convert to base64 to match the hashing process
        password_hash_b64 = base64.b64encode(password_hash_bytes).decode('utf-8')
        password_to_verify = password_hash_b64
    else:
        password_to_verify = plain_password
    
    # Ensure the final password is not longer than 72 bytes when encoded
    final_bytes = password_to_verify.encode('utf-8')
    if len(final_bytes) > 72:
        # Truncate to 72 bytes
        password_to_verify = password_to_verify[:72]
    
    # Verify using bcrypt directly
    try:
        return bcrypt.checkpw(password_to_verify.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        # Log the error for debugging
        print(f"JWT decode error: {e}")
        return None
    except Exception as e:
        # Log any other errors
        print(f"Token decode error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get the current authenticated user from JWT."""
    token = credentials.credentials
    
    # Decode and verify token
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None or not isinstance(user_id, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Look up user (in production, query database)
    # Note: users_db is in-memory, so users are lost on server restart
    user = None
    for email, user_data in users_db.items():
        if user_data["id"] == user_id:
            user = user_data
            break
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

