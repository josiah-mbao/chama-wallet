# backend/config_test.py
from pydantic_settings import BaseSettings

class TestSettings(BaseSettings):
    DATABASE_URL: str = "sqlite+pysqlite:///:memory:"  # in-memory DB, fast
    SECRET_KEY: str = "test_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = TestSettings()