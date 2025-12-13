"""Configuration management using environment variables."""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


# Get the directory where this config file is located
_CONFIG_DIR = Path(__file__).parent.parent
_ENV_FILE = _CONFIG_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-5-mini"  # Default OpenAI model
    openai_temperature: float = 1.0  # Default temperature (1.0 works for all models)
    
    # AI Provider Configuration
    ai_provider: str = "openai"  # "openai" or "openai-compatible"
    ai_base_url: Optional[str] = None
    ai_api_key: Optional[str] = None
    
    # JWT Configuration
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8001
    backend_base_url: str = "http://localhost:8001"  # Backend URL for email confirmation links (configurable for production)
    
    # Email Configuration (Resend)
    resend_api_key: str
    app_base_url: str = "http://localhost:5173"  # Frontend URL for confirmation links
    email_from_address: str
    email_from_name: str = "Brousla App"
    
    # Google OAuth Configuration
    google_oauth_client_id: str
    google_oauth_client_secret: str
    # Note: Google requires HTTP/HTTPS redirect URIs, not custom protocols
    # We use localhost HTTP, then redirect to custom protocol for Electron
    # The redirect URI will be computed as http://localhost:{port}/auth/google/callback
    
    # Stripe Configuration
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_basic_price_id: Optional[str] = None
    stripe_plus_price_id: Optional[str] = None
    stripe_pro_price_id: Optional[str] = None
    
    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

