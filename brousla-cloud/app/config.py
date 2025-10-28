from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_private_key_pem: str
    jwt_public_key_pem: str
    stripe_secret: str
    stripe_wh_secret: str
    stripe_price_id_pro: str = "price_pro"
    stripe_price_id_team: str = "price_team"
    base_url: str = "http://localhost:8000"
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    jwt_license_token_expire_days: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
