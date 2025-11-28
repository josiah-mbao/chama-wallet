# tests/integration/test_api.py
import pytest
from backend.models.user import User, UserRole
from backend.security import get_password_hash

@pytest.fixture
def init_db(db_session):
    """Initialize test data"""
    # Clear existing test users to avoid conflicts
    from sqlalchemy import text
    db_session.execute(text("DELETE FROM memberships"))
    db_session.execute(text("DELETE FROM contributions"))
    db_session.execute(text("DELETE FROM chamas"))
    db_session.execute(text("DELETE FROM users"))
    db_session.commit()

    # Create users
    owner = User(email="owner@test.com", first_name="Test", last_name="Owner",
                hashed_password=get_password_hash("ownerpass"),
                role=UserRole.owner, is_active=True)
    treasurer = User(email="treasurer@test.com", first_name="Test", last_name="Treasurer",
                    hashed_password=get_password_hash("treasurerpass"),
                    role=UserRole.treasurer, is_active=True)
    member = User(email="member@test.com", first_name="Test", last_name="Member",
                 hashed_password=get_password_hash("memberpass"),
                 role=UserRole.member, is_active=True)
    db_session.add_all([owner, treasurer, member])
    db_session.commit()

    yield db_session

# ---- Helpers ----
def login_get_token(client, email, password):
    response = client.post("/users/token", data={"username": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

# ---- Chama Tests ----
def test_create_chama(client, init_db):
    token = login_get_token(client, "owner@test.com", "ownerpass")
    response = client.post(
        "/chamas/",
        json={"name": "Test Chama", "description": "Test"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201

def test_list_user_chamas(client, init_db):
    token = login_get_token(client, "owner@test.com", "ownerpass")
    response = client.get("/chamas/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_get_chama_details(client, init_db):
    # First create a chama
    token = login_get_token(client, "owner@test.com", "ownerpass")
    create_response = client.post(
        "/chamas/",
        json={"name": "Test Chama Details", "description": "Details Test"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert create_response.status_code == 201
    chama_id = create_response.json()["id"]

    # Now get its details
    response = client.get(f"/chamas/{chama_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
