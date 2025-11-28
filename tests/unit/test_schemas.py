import pytest
from pydantic import ValidationError
from backend.schemas import UserCreate, ChamaCreate, ContributionCreate

def test_user_create_valid():
    user = UserCreate(
        email="a@b.com",
        first_name="Test",
        last_name="User",
        password="1234"
    )
    assert user.email == "a@b.com"
    assert user.first_name == "Test"
    assert user.last_name == "User"

def test_user_create_invalid_email():
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="1234")

def test_chama_create_valid():
    chama = ChamaCreate(name="Test Chama")
    assert chama.name == "Test Chama"

def test_contribution_create_valid():
    contrib = ContributionCreate(amount=100.0)
    assert contrib.amount == 100.0
