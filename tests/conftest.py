# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- 0. Use a file-based SQLite DB for tests ---
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing"

from backend.database import Base, get_db, engine as app_engine
from backend.main import app
from backend.config_test import settings

# --- 1. Create a dedicated test engine and session for testing ---
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# --- 2. Create tables once per test session ---
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests and drop them after session ends."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # remove test.db file after tests
    if "sqlite" in settings.DATABASE_URL and os.path.exists("./test.db"):
        os.remove("./test.db")

# --- 3. Provide a fresh DB session per test ---
@pytest.fixture(scope="function")
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

# --- 4. Provide a TestClient with overridden DB dependency ---
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
