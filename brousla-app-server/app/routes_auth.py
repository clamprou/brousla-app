"""Authentication routes: register, login, and user info."""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from app.models import (
    UserRegister, UserLogin, Token, User, 
    EmailConfirmationRequest, ResendConfirmationRequest, MessageResponse
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from app.database import (
    get_user_by_email, create_user, update_user_email_verified,
    get_user_by_verification_token, update_user_verification_token,
    update_user_last_confirmation_email_sent, get_user_last_confirmation_email_sent
)
from app.email_service import send_confirmation_email
from app.config import settings
from urllib.parse import urlencode

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister):
    """
    Register a new user.
    
    Sends a confirmation email. User must confirm email before logging in.
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
    
    # Generate email verification token
    verification_token = str(uuid.uuid4())
    token_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    
    # Create user in database (not verified yet)
    create_user(
        user_id, 
        user_data.email, 
        hashed_password,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_token_expires=token_expires
    )
    
    # Generate confirmation URL - point to backend, which will redirect to frontend
    backend_url = f"http://localhost:{settings.port}"
    confirmation_url = f"{backend_url}/auth/confirm-email?token={verification_token}"
    
    # Send confirmation email
    try:
        send_confirmation_email(user_data.email, verification_token, confirmation_url)
    except Exception as e:
        # If email fails, we still created the user, but log the error
        print(f"Failed to send confirmation email: {e}")
        # Don't fail registration if email fails - user can request resend
    
    return MessageResponse(message="Registration successful. Please check your email to confirm your account.")


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login with email and password.
    
    Returns a JWT access token. Email must be verified first.
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
    
    # Check if email is verified
    if not user_record.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email address before logging in. Check your inbox for the confirmation email."
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user_record["id"]})
    
    return Token(access_token=access_token)


@router.get("/confirm-email")
async def confirm_email(token: str = Query(..., description="Email verification token")):
    """
    Confirm email address using verification token (GET endpoint for email links).
    Redirects to frontend with success or error status.
    """
    # Find user by verification token
    user_record = get_user_by_verification_token(token)
    
    # Prepare redirect URL base
    frontend_url = settings.app_base_url
    redirect_params = {}
    
    if not user_record:
        # Invalid token - redirect with error
        redirect_params = {
            "status": "error",
            "message": "Invalid or expired confirmation token"
        }
        electron_url = f"brousla://email-confirmation?{urlencode(redirect_params)}"
        redirect_url = electron_url
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if token is expired
    if user_record.get("email_verification_token_expires"):
        expires_at = datetime.fromisoformat(user_record["email_verification_token_expires"])
        if datetime.utcnow() > expires_at:
            redirect_params = {
                "status": "error",
                "message": "Confirmation token has expired. Please request a new confirmation email."
            }
            electron_url = f"brousla://email-confirmation?{urlencode(redirect_params)}"
            redirect_url = electron_url
            return RedirectResponse(url=redirect_url, status_code=302)
    
    # Check if already verified
    if user_record.get("email_verified", False):
        redirect_params = {
            "status": "success",
            "message": "Email address is already verified. You can log in."
        }
        electron_url = f"brousla://email-confirmation?{urlencode(redirect_params)}"
        redirect_url = electron_url
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Mark email as verified and clear token
    update_user_email_verified(user_record["id"], True)
    update_user_verification_token(user_record["id"], None, None)
    
    # Success - redirect to frontend using custom protocol for Electron app
    redirect_params = {
        "status": "success",
        "message": "Email address confirmed successfully. You can now log in."
    }
    # Use custom protocol for Electron app, fallback to HTTP for web
    electron_url = f"brousla://email-confirmation?{urlencode(redirect_params)}"
    http_url = f"{frontend_url}/email-confirmation?{urlencode(redirect_params)}"
    # Redirect to custom protocol (Electron will handle it), with HTTP fallback
    # Note: Browsers will show an error for custom protocols, but Electron will catch it
    redirect_url = electron_url
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/confirm-email", response_model=MessageResponse)
async def confirm_email_post(request: EmailConfirmationRequest):
    """
    Confirm email address using verification token (POST endpoint for API calls).
    """
    # Find user by verification token
    user_record = get_user_by_verification_token(request.token)
    
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired confirmation token"
        )
    
    # Check if token is expired
    if user_record.get("email_verification_token_expires"):
        expires_at = datetime.fromisoformat(user_record["email_verification_token_expires"])
        if datetime.utcnow() > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation token has expired. Please request a new confirmation email."
            )
    
    # Check if already verified
    if user_record.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already verified"
        )
    
    # Mark email as verified and clear token
    update_user_email_verified(user_record["id"], True)
    update_user_verification_token(user_record["id"], None, None)
    
    return MessageResponse(message="Email address confirmed successfully. You can now log in.")


@router.post("/resend-confirmation", response_model=MessageResponse)
async def resend_confirmation(request: ResendConfirmationRequest):
    """
    Resend confirmation email. Has a 5-minute cooldown between requests.
    """
    # Find user
    user_record = get_user_by_email(request.email)
    
    if not user_record:
        # Don't reveal if email exists or not (security best practice)
        return MessageResponse(message="If an account with this email exists and is not verified, a confirmation email has been sent.")
    
    # Check if already verified
    if user_record.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already verified"
        )
    
    # Check cooldown period (5 minutes = 300 seconds)
    last_sent = get_user_last_confirmation_email_sent(user_record["id"])
    if last_sent:
        last_sent_dt = datetime.fromisoformat(last_sent)
        time_since_last = (datetime.utcnow() - last_sent_dt).total_seconds()
        
        if time_since_last < 300:  # 5 minutes
            remaining_seconds = int(300 - time_since_last)
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining_minutes} minute(s) and {remaining_secs} second(s) before requesting another confirmation email."
            )
    
    # Generate new verification token
    verification_token = str(uuid.uuid4())
    token_expires = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    
    # Update token in database
    update_user_verification_token(user_record["id"], verification_token, token_expires)
    
    # Update last sent timestamp
    update_user_last_confirmation_email_sent(user_record["id"], datetime.utcnow().isoformat())
    
    # Generate confirmation URL - point to backend, which will redirect to frontend
    backend_url = f"http://localhost:{settings.port}"
    confirmation_url = f"{backend_url}/auth/confirm-email?token={verification_token}"
    
    # Send confirmation email
    try:
        send_confirmation_email(request.email, verification_token, confirmation_url)
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send confirmation email. Please try again later."
        )
    
    return MessageResponse(message="Confirmation email has been sent. Please check your inbox.")


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    return User(
        id=current_user["id"],
        email=current_user["email"],
        email_verified=current_user.get("email_verified", False)
    )

