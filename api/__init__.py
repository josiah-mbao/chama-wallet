"""
API versioning for Chama Wallet SaaS platform.
Provides backward-compatible API evolution.
"""
from fastapi import HTTPException

# API Version Configuration
SUPPORTED_VERSIONS = ["v1", "v2"]
DEPRECATED_VERSIONS = []  # Will contain versions scheduled for removal
DEFAULT_VERSION = "v1"

class APIVersionError(HTTPException):
    def __init__(self, version: str):
        super().__init__(
            status_code=400,
            detail=f"Unsupported API version: {version}. Supported versions: {', '.join(SUPPORTED_VERSIONS)}"
        )
