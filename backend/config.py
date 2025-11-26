import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REDIS_URL: str = "redis://redis:6379/0"

    # Paystack payment integration settings
    PAYSTACK_SECRET_KEY: str = "sk_test_default_for_ci_cd"
    PAYSTACK_PUBLIC_KEY: str = "pk_test_default_for_ci_cd"
    PAYSTACK_WEBHOOK_SECRET: str = ""  # Optional webhook signature verification

    # Extract Redis host and port for easier access
    @property
    def REDIS_HOST(self) -> str:
        """Extract Redis host from REDIS_URL."""
        if self.REDIS_URL.startswith("redis://"):
            url_parts = self.REDIS_URL.replace("redis://", "").split(":")
            return url_parts[0] if len(url_parts) > 0 else "redis"
        return "redis"

    @property
    def REDIS_PORT(self) -> int:
        """Extract Redis port from REDIS_URL."""
        if self.REDIS_URL.startswith("redis://"):
            url_parts = self.REDIS_URL.replace("redis://", "").split(":")
            if len(url_parts) > 1:
                port_db = url_parts[1].split("/")
                return int(port_db[0]) if port_db[0].isdigit() else 6379
        return 6379

    @property
    def REDIS_DB(self) -> int:
        """Extract Redis db from REDIS_URL."""
        if self.REDIS_URL.startswith("redis://"):
            url_parts = self.REDIS_URL.replace("redis://", "").split("/")
            if len(url_parts) > 1:
                return int(url_parts[-1]) if url_parts[-1].isdigit() else 0
        return 0

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", "backend/.env"),  # Default to .env
        env_file_encoding="utf-8"
    )

settings = Settings()
