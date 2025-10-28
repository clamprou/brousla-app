import pytest
from jose import jwt
from app.config import settings


def test_get_entitlements_after_registration(client):
    """Test getting entitlements after registration (should have free plan)"""
    # Register user
    register_response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    token = register_response.json()["access_token"]
    
    # Get entitlements
    response = client.get(
        "/entitlements",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "license_jwt" in data
    
    # Decode and verify license JWT
    license_jwt = data["license_jwt"]
    decoded = jwt.decode(
        license_jwt,
        settings.jwt_public_key_pem,
        algorithms=[settings.jwt_algorithm]
    )
    
    assert decoded["plan"] == "FREE"
    assert decoded["type"] == "license"
    assert "limits" in decoded
    assert "exp" in decoded


def test_get_entitlements_without_auth(client):
    """Test getting entitlements without authentication"""
    response = client.get("/entitlements")
    assert response.status_code == 403  # No auth header


def test_device_registration(client):
    """Test device registration"""
    # Register and login user
    register_response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    token = register_response.json()["access_token"]
    
    # Register device
    response = client.post(
        "/devices/register",
        json={"device_id": "device-123", "app_version": "1.0.0"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == "device-123"
    assert "successfully" in data["message"]


def test_license_jwt_structure(client):
    """Test that license JWT contains required claims"""
    # Register user
    register_response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    token = register_response.json()["access_token"]
    
    # Get entitlements
    response = client.get(
        "/entitlements",
        headers={"Authorization": f"Bearer {token}"}
    )
    license_jwt = response.json()["license_jwt"]
    
    # Decode license JWT
    decoded = jwt.decode(
        license_jwt,
        settings.jwt_public_key_pem,
        algorithms=[settings.jwt_algorithm]
    )
    
    # Check required claims
    required_claims = ["sub", "plan", "limits", "seats", "device_max", "exp"]
    for claim in required_claims:
        assert claim in decoded, f"Missing required claim: {claim}"
