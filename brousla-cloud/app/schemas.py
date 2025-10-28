from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, Dict


class RegisterRequest(BaseModel):
    email: EmailStr
    pwd: str


class LoginRequest(BaseModel):
    email: EmailStr
    pwd: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DeviceRegisterRequest(BaseModel):
    device_id: str
    app_version: Optional[str] = None


class DeviceRegisterResponse(BaseModel):
    device_id: str
    message: str


class EntitlementsResponse(BaseModel):
    license_jwt: str


class UsageReportRequest(BaseModel):
    type: str
    qty: float = 1.0


class UsageReportResponse(BaseModel):
    message: str
    total_today: float


class CheckoutSessionRequest(BaseModel):
    plan: str  # "PRO" or "TEAM"


class CheckoutSessionResponse(BaseModel):
    url: str


class PortalSessionResponse(BaseModel):
    url: str


class JWKResponse(BaseModel):
    keys: list
