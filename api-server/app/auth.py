"""Authentication utilities: JWT, password hashing, and auth dependencies."""
import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.database import get_user_by_id

# JWT token bearer scheme
security = HTTPBearer()


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
        # Truncate to 72 bytes (not characters) to handle multi-byte UTF-8 correctly
        password_to_hash = final_bytes[:72].decode('utf-8', errors='ignore')
    
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
        # Truncate to 72 bytes (not characters) to handle multi-byte UTF-8 correctly
        password_to_verify = final_bytes[:72].decode('utf-8', errors='ignore')
    
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
    
    # Convert datetime to Unix timestamp (integer) for JWT exp claim
    to_encode.update({"exp": int(expire.timestamp())})
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
    
    # Look up user in database
    user = get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

