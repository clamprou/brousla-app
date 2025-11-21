"""Authentication routes: register, login, and user info."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.models import UserRegister, UserLogin, Token, User
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.database import get_user_by_email, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user.
    
    Returns a JWT access token (user is automatically logged in).
    """
    # Check if user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate user ID
    user_id = str(uuid.uuid4())
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user in database
    create_user(user_id, user_data.email, hashed_password)
    
    # Create access token (auto-login after registration)
    access_token = create_access_token(data={"sub": user_id})
    
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login with email and password.
    
    Returns a JWT access token.
    """
    # Find user
    user_record = get_user_by_email(credentials.email)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(credentials.password, user_record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user_record["id"]})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    return User(
        id=current_user["id"],
        email=current_user["email"]
    )

