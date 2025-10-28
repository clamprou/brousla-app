import pytest
from fastapi.testclient import TestClient


def test_register_user(client):
    """Test user registration"""
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client):
    """Test registering with duplicate email"""
    # First registration
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    
    # Second registration with same email
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password456"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client):
    """Test successful login"""
    # Register user
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    
    # Login
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Test login with wrong password"""
    # Register user
    client.post(
        "/auth/register",
        json={"email": "test@example.com", "pwd": "password123"}
    )
    
    # Login with wrong password
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "pwd": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Test login with nonexistent user"""
    response = client.post(
        "/auth/login",
        json={"email": "notfound@example.com", "pwd": "password123"}
    )
    assert response.status_code == 401
