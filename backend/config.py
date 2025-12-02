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

    # SSL/HTTPS Configuration
    ENABLE_HTTPS: bool = False  # Set to True for production
    SSL_CERT_PATH: str = "/app/ssl/cert.pem"  # Path to SSL certificate
    SSL_KEY_PATH: str = "/app/ssl/key.pem"    # Path to SSL private key
    FORCE_HTTPS_REDIRECT: bool = False       # Force HTTP to HTTPS redirect

    # Security Headers Configuration
    ENABLE_SECURITY_HEADERS: bool = True     # Enable comprehensive security headers
    CSP_ENABLED: bool = True                 # Enable Content Security Policy
    HSTS_MAX_AGE: int = 31536000             # HSTS max-age in seconds (1 year)
    HSTS_INCLUDE_SUBDOMAINS: bool = True     # Include subdomains in HSTS
    HSTS_PRELOAD: bool = False               # Enable HSTS preload (only for production)

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
