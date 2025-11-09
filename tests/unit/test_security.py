from datetime import timedelta
from backend.security import get_password_hash, verify_password, create_access_token, decode_access_token

def test_password_hashing():
    password = "secret123"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong", hashed)

def test_create_decode_jwt():
    data = {"sub": "user@example.com"}
    token = create_access_token(data, expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload.email == "user@example.com"
