# tests/test_users.py
import pytest
from fastapi.testclient import TestClient
from backend.schemas import UserCreate

def test_register_and_login_user(client: TestClient):
    """Test registering a new user and logging in."""

    # --- 1. Register a new user ---
    user_data = {
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "password123"
    }
    response = client.post("/users/", json=user_data)
    assert response.status_code == 201, f"Unexpected status code: {response.status_code}"

    data = response.json()
    assert "id" in data
    assert data["email"] == user_data["email"]
    assert data["first_name"] == user_data["first_name"]
    assert data["last_name"] == user_data["last_name"]

    # --- 2. Login with the registered user ---
    login_data = {"username": user_data["email"], "password": user_data["password"]}
    login_response = client.post(
        "/users/token",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
