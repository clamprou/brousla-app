"""Authentication routes: register, login, and user info."""
import uuid
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
import httpx
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

# In-memory storage for OAuth state (in production, use Redis or database)
# Maps state token to dict with timestamp and optionally token/error
# Format: {state: {"timestamp": datetime, "token": str | None, "error": str | None}}
_oauth_states = {}

# Google OAuth endpoints
GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"


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
    confirmation_url = f"{settings.backend_base_url}/auth/confirm-email?token={verification_token}"
    
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
    
    # Check if user has a password (OAuth users don't have passwords)
    if not user_record.get("hashed_password"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account was created with Google. Please sign in with Google instead.",
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
    confirmation_url = f"{settings.backend_base_url}/auth/confirm-email?token={verification_token}"
    
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


def _create_or_get_google_user(email: str) -> dict:
    """
    Create a new user from Google OAuth or return existing user.
    
    Args:
        email: User's email from Google profile
        
    Returns:
        User dictionary
    """
    # Check if user already exists
    existing_user = get_user_by_email(email)
    
    if existing_user:
        # User exists - if email is not verified, verify it now (Google verifies emails)
        if not existing_user.get("email_verified", False):
            update_user_email_verified(existing_user["id"], True)
            # Clear verification token if it exists
            update_user_verification_token(existing_user["id"], None, None)
            # Refresh user data
            existing_user = get_user_by_email(email)
        return existing_user
    
    # Create new user (OAuth users have no password and email is verified)
    user_id = str(uuid.uuid4())
    create_user(
        user_id=user_id,
        email=email,
        hashed_password=None,  # OAuth users don't have passwords
        email_verified=True,  # Google verifies emails
        email_verification_token=None,
        email_verification_token_expires=None
    )
    
    # Return the newly created user
    return get_user_by_email(email)


@router.get("/google/login")
async def google_login():
    """
    Initiate Google OAuth flow.
    
    Returns the Google OAuth authorization URL for the client to open in external browser.
    """
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "timestamp": datetime.utcnow(),
        "token": None,
        "error": None
    }
    
    # Clean up old states (older than 10 minutes)
    cutoff_time = datetime.utcnow() - timedelta(minutes=10)
    expired_states = [s for s, data in _oauth_states.items() 
                     if isinstance(data, dict) and data.get("timestamp", datetime.utcnow()) < cutoff_time
                     or not isinstance(data, dict) and data < cutoff_time]  # Backward compatibility
    for expired_state in expired_states:
        del _oauth_states[expired_state]
    
    # Use HTTP localhost redirect URI (Google requires HTTP/HTTPS, not custom protocols)
    # We'll redirect to custom protocol after processing the callback
    redirect_uri = f"http://localhost:{settings.port}/auth/google/callback"
    
    # Build authorization URL
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account"  # Force account selection
    }
    
    auth_url = f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"
    
    # Return JSON with auth URL and state token for polling
    # Client will open this URL in external browser using shell.openExternal()
    # and poll /auth/google/status/{state} to check completion
    return JSONResponse(content={"auth_url": auth_url, "state": state})


@router.get("/google/status/{state}")
async def google_oauth_status(state: str):
    """
    Check OAuth status by state token.
    
    Returns the JWT token if authentication completed successfully,
    or an error message if authentication failed.
    Used for polling by the frontend.
    """
    # Check if state exists
    if state not in _oauth_states:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth state not found or expired"
        )
    
    # Get state data (handle both old and new format)
    state_data = _oauth_states.get(state)
    if isinstance(state_data, dict):
        # New format
        token = state_data.get("token")
        error = state_data.get("error")
        
        if token:
            # Success - return token and mark as consumed (optional: can keep for a bit)
            return JSONResponse(content={
                "status": "success",
                "token": token
            })
        elif error:
            # Error occurred
            return JSONResponse(content={
                "status": "error",
                "message": error
            })
        else:
            # Still pending
            return JSONResponse(content={
                "status": "pending"
            })
    else:
        # Old format - just a timestamp, means still pending
        return JSONResponse(content={
            "status": "pending"
        })


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for CSRF protection"),
    error: str = Query(None, description="Error from Google OAuth")
):
    """
    Handle Google OAuth callback.
    
    Exchanges authorization code for user info, creates/updates user,
    and redirects to frontend with JWT token.
    """
    # Check for OAuth errors
    if error:
        error_message = f"Google OAuth error: {error}"
        # Store error in state for polling if state exists
        if state in _oauth_states:
            state_data = _oauth_states.get(state)
            if isinstance(state_data, dict):
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
            else:
                _oauth_states[state] = {
                    "timestamp": state_data if isinstance(state_data, datetime) else datetime.utcnow(),
                    "token": None,
                    "error": error_message
                }
        redirect_params = {
            "status": "error",
            "message": error_message
        }
        electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>{error}</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)
    
    # Validate state token
    if state not in _oauth_states:
        # Store error for polling
        _oauth_states[state] = {
            "timestamp": datetime.utcnow(),
            "token": None,
            "error": "Invalid or expired OAuth state token"
        }
        redirect_params = {
            "status": "error",
            "message": "Invalid or expired OAuth state token"
        }
        electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>Invalid or expired OAuth state token</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)
    
    # Get state data (handle both old format for backward compatibility)
    state_data = _oauth_states.get(state)
    if isinstance(state_data, dict):
        # New format - state is already a dict
        pass
    else:
        # Old format - convert to new format
        _oauth_states[state] = {
            "timestamp": state_data if isinstance(state_data, datetime) else datetime.utcnow(),
            "token": None,
            "error": None
        }
        state_data = _oauth_states[state]
    
    try:
        # Use HTTP localhost redirect URI (must match what we sent to Google)
        redirect_uri = f"http://localhost:{settings.port}/auth/google/callback"
        
        # Exchange authorization code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                error_detail = token_response.text
                error_message = f"Failed to exchange authorization code: {error_detail}"
                # Store error in state for polling
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
                redirect_params = {
                    "status": "error",
                    "message": error_message
                }
                electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>Failed to exchange authorization code</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
                """
                return HTMLResponse(content=html_content)
            
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                error_message = "No access token received from Google"
                # Store error in state for polling
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
                redirect_params = {
                    "status": "error",
                    "message": error_message
                }
                electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>No access token received from Google</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
                """
                return HTMLResponse(content=html_content)
            
            # Get user info from Google
            userinfo_response = await client.get(
                GOOGLE_USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if userinfo_response.status_code != 200:
                error_message = "Failed to get user info from Google"
                # Store error in state for polling
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
                redirect_params = {
                    "status": "error",
                    "message": error_message
                }
                electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>Failed to get user info from Google</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
                """
                return HTMLResponse(content=html_content)
            
            userinfo = userinfo_response.json()
            email = userinfo.get("email")
            
            if not email:
                error_message = "No email address in Google profile"
                # Store error in state for polling
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
                redirect_params = {
                    "status": "error",
                    "message": error_message
                }
                electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
                html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>No email address in Google profile</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
                """
                return HTMLResponse(content=html_content)
            
            # Create or get user
            user = _create_or_get_google_user(email)
            
            # Generate JWT token
            access_token_jwt = create_access_token(data={"sub": user["id"]})
            
            # Store token in state for polling (don't delete state yet - frontend needs to poll it)
            _oauth_states[state] = {
                "timestamp": state_data.get("timestamp", datetime.utcnow()),
                "token": access_token_jwt,
                "error": None
            }
            
            # Serve simple success page
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Successful</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            backdrop-filter: blur(10px);
            max-width: 500px;
        }}
        h2 {{
            margin-top: 0;
            margin-bottom: 1rem;
        }}
        p {{
            margin: 0.5rem 0;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Successful!</h2>
        <p>You may now return to the application.</p>
        <p style="font-size: 0.9em; opacity: 0.8; margin-top: 1rem;">You can close this window.</p>
    </div>
</body>
</html>
            """
            return HTMLResponse(content=html_content)
            
    except Exception as e:
        print(f"Google OAuth callback error: {e}")
        error_message = f"OAuth callback error: {str(e)}"
        # Store error in state for polling if state exists
        if state in _oauth_states:
            state_data = _oauth_states.get(state)
            if isinstance(state_data, dict):
                _oauth_states[state] = {
                    "timestamp": state_data.get("timestamp", datetime.utcnow()),
                    "token": None,
                    "error": error_message
                }
            else:
                _oauth_states[state] = {
                    "timestamp": state_data if isinstance(state_data, datetime) else datetime.utcnow(),
                    "token": None,
                    "error": error_message
                }
        redirect_params = {
            "status": "error",
            "message": error_message
        }
        electron_url = f"brousla://google-oauth-callback?{urlencode(redirect_params)}"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sign-In Error</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #dc2626;
            color: white;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Sign-In Error</h2>
        <p>An error occurred during sign-in</p>
        <p style="font-size: 0.9em; opacity: 0.8;">You can close this window.</p>
    </div>
    <script>
        window.location.href = '{electron_url}';
    </script>
</body>
</html>
        """
        return HTMLResponse(content=html_content)

