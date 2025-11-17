# tests/conftest.py
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- 0. Use a file-based SQLite DB for tests ---
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing"
# Disable Redis for tests (will use fake connection that fails gracefully)
os.environ["REDIS_URL"] = "redis://localhost:9999/0"  # Non-existent Redis URL

from backend.database import Base, get_db, engine as app_engine
from backend.main import app
from backend.config_test import settings

# Mock Celery tasks for tests to avoid Redis connections
from unittest.mock import MagicMock, patch
import pytest

# Mock all Celery task delay calls
celery_mock = MagicMock()
celery_mock.delay = MagicMock()

# --- 1. Create a dedicated test engine and session for testing ---
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# --- Disable rate limiting for tests ---
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class NoOpRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that disables rate limiting for tests"""
    async def dispatch(self, request: Request, call_next):
        # Skip all rate limiting for tests
        response = await call_next(request)
        return response

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

# --- 4. Mock Celery tasks to avoid Redis connections ---
@pytest.fixture(scope="function", autouse=True)
def mock_celery_tasks():
    """Mock all Celery task .delay() calls to avoid Redis connections during tests"""
    with patch('backend.tasks.notifications.notify_chama_created.delay'), \
         patch('backend.tasks.notifications.notify_member_added.delay'), \
         patch('backend.tasks.notifications.notify_contribution_created.delay'), \
         patch('backend.tasks.analytics.recompute_chama_summaries.delay'), \
         patch('backend.tasks.analytics.precompute_chama_analytics.delay'):
        yield

# --- 5. Provide a TestClient with overridden DB dependency ---
@pytest.fixture(scope="function")
def client(db_session, mock_celery_tasks):
    # Create a test app without rate limiting middleware
    from fastapi import FastAPI
    from backend.routers.users import router as users_router
    from backend.routers.chamas import router as chamas_router
    from backend.routers.members import router as members_router


    test_app = FastAPI(title="Test Chama Wallet API")
    # Skip all middleware for tests to avoid conflicts
    # test_app.add_middleware(RequestLoggingMiddleware)

    test_app.include_router(users_router, prefix="/users", tags=["users"])
    test_app.include_router(chamas_router, prefix="/chamas", tags=["chamas"])
    test_app.include_router(members_router, prefix="/chamas/{chama_id}", tags=["members"])

    def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db
    with TestClient(test_app) as c:
        yield c
    test_app.dependency_overrides.clear()
