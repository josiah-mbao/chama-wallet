"""
Unit tests for security headers middleware.
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_security_headers_enabled(client):
    """Test that security headers are added when enabled."""
    # Ensure security headers are enabled in settings
    original_value = settings.ENABLE_SECURITY_HEADERS
    settings.ENABLE_SECURITY_HEADERS = True

    try:
        response = client.get("/")

        # Check essential security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("Permissions-Policy") is not None
        assert response.headers.get("Cross-Origin-Embedder-Policy") == "require-corp"
        assert response.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
        assert response.headers.get("Cross-Origin-Resource-Policy") == "same-origin"
        assert response.headers.get("Origin-Agent-Cluster") == "?1"
        assert response.headers.get("X-DNS-Prefetch-Control") == "off"

        # Check Content Security Policy if enabled
        if settings.CSP_ENABLED:
            assert "Content-Security-Policy" in response.headers

    finally:
        settings.ENABLE_SECURITY_HEADERS = original_value


def test_security_headers_disabled(client):
    """Test that security headers are not added when disabled."""
    # Disable security headers
    original_value = settings.ENABLE_SECURITY_HEADERS
    settings.ENABLE_SECURITY_HEADERS = False

    try:
        response = client.get("/")

        # Check that security headers are not present
        assert "X-Content-Type-Options" not in response.headers
        assert "X-Frame-Options" not in response.headers
        assert "X-XSS-Protection" not in response.headers

    finally:
        settings.ENABLE_SECURITY_HEADERS = original_value


def test_hsts_header_with_https(client):
    """Test HSTS header is added when HTTPS is enabled."""
    # Enable HTTPS
    original_https = settings.ENABLE_HTTPS
    original_headers = settings.ENABLE_SECURITY_HEADERS
    settings.ENABLE_HTTPS = True
    settings.ENABLE_SECURITY_HEADERS = True

    try:
        response = client.get("/")

        # Check HSTS header
        hsts_header = response.headers.get("Strict-Transport-Security")
        assert hsts_header is not None
        assert "max-age=" in hsts_header

        if settings.HSTS_INCLUDE_SUBDOMAINS:
            assert "includeSubDomains" in hsts_header

        if settings.HSTS_PRELOAD:
            assert "preload" in hsts_header

    finally:
        settings.ENABLE_HTTPS = original_https
        settings.ENABLE_SECURITY_HEADERS = original_headers


def test_hsts_header_without_https(client):
    """Test HSTS header is not added when HTTPS is disabled."""
    # Disable HTTPS
    original_https = settings.ENABLE_HTTPS
    original_headers = settings.ENABLE_SECURITY_HEADERS
    settings.ENABLE_HTTPS = False
    settings.ENABLE_SECURITY_HEADERS = True

    try:
        response = client.get("/")

        # Check HSTS header is not present
        assert "Strict-Transport-Security" not in response.headers

    finally:
        settings.ENABLE_HTTPS = original_https
        settings.ENABLE_SECURITY_HEADERS = original_headers
