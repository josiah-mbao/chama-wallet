import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
from backend.crud import create_user, get_user_by_email
from backend.schemas import UserCreate

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_create_user(db_session):
    user_in = UserCreate(email="test@example.com", password="password123")
    user = create_user(db_session, user_in)
    assert user.email == "test@example.com"
    fetched = get_user_by_email(db_session, "test@example.com")
    assert fetched.id == user.id
