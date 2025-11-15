# tests/integration/test_api_full.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.main import app
from backend.database import get_db, Base
from backend.models.user import User, UserRole
from backend.models.membership import Membership, MembershipRole
from backend.models.chama import Chama
from backend.security import get_password_hash

# ---- Setup test database ----
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_full.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ---- Fixtures ----
@pytest.fixture(scope="module")
def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Create users
    owner = User(email="owner@test.com", hashed_password=get_password_hash("ownerpass"), role=UserRole.owner, is_active=True)
    treasurer = User(email="treasurer@test.com", hashed_password=get_password_hash("treasurerpass"), role=UserRole.treasurer, is_active=True)
    member = User(email="member@test.com", hashed_password=get_password_hash("memberpass"), role=UserRole.member, is_active=True)
    db.add_all([owner, treasurer, member])
    db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

# ---- Helpers ----
def login_get_token(email, password):
    response = client.post("/users/token", data={"username": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

# ---- Chama Tests ----
def test_create_chama(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.post(
        "/chamas/",
        json={"name": "Test Chama", "description": "A test Chama"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Chama"
    assert data["memberships"][0]["role"] == "owner"

def test_list_user_chamas(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.get("/chamas/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0

def test_get_chama_details(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.get("/chamas/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1

# ---- Membership Tests ----
def test_join_chama(init_db):
    token = login_get_token("member@test.com", "memberpass")
    response = client.post("/members/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    data = response.json()
    assert data["chama_id"] == 1
    assert data["role"] == "member"

def test_add_member_by_owner(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.post("/members/1/add-member", json={"member_email": "treasurer@test.com"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_membership_list(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.get("/members/1", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    emails = [m["user"]["email"] for m in data]
    assert "member@test.com" in emails

# ---- Contribution Tests ----
def test_add_contribution_by_treasurer(init_db):
    token = login_get_token("treasurer@test.com", "treasurerpass")
    response = client.post("/members/1/add-contribution", json={"amount": 500}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 500

def test_role_restriction(init_db):
    token = login_get_token("member@test.com", "memberpass")
    response = client.post("/members/1/add-contribution", json={"amount": 500}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

# ---- Edge Cases ----
def test_nonexistent_chama(init_db):
    token = login_get_token("owner@test.com", "ownerpass")
    response = client.get("/chamas/999", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404

def test_non_member_access(init_db):
    token = login_get_token("member@test.com", "memberpass")
    # Access another chama (id=2 does not exist)
    response = client.get("/chamas/2", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in [403, 404]
