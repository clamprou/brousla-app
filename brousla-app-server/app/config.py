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
    openai_model: str = "gpt-4-turbo-preview"  # Default OpenAI model
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
    
    class Config:
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

