# backend/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # This will load from an .env file by default
    # It will look for a variable named "DATABASE_URL"
    DATABASE_URL: str

    # This tells Pydantic to look for a .env file
    # We'll create this file next
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
