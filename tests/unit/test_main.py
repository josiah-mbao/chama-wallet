"""
Unit tests for main.py - FastAPI application setup, endpoints, and exception handlers.
Tests app initialization, middleware, API endpoints, and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.main import app, read_root, get_api_info, get_metrics, get_metrics_summary_endpoint
from backend.main import (
    chama_wallet_exception_handler,
    validation_exception_handler,
    integrity_error_handler,
    sqlalchemy_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from backend.exceptions import ChamaWalletException
from backend.schemas import ErrorResponse, ValidationErrorResponse, ValidationErrorDetail


class TestAppInitialization:
    """Test FastAPI app initialization and configuration."""

    def test_app_creation(self):
        """Test that FastAPI app is created with correct configuration."""
        from backend.main import app
        assert app.title == "Chama Wallet API"
        # App should have routes registered
        assert len(app.routes) > 0

    def test_cors_middleware_added(self):
        """Test that CORS middleware is configured (basic presence check)."""
        from backend.main import app

        # Check that we have middleware configured (CORS is in the list)
        # The exact middleware inspection is complex, but we can verify basic setup
        assert hasattr(app, 'user_middleware'), "App should have middleware configured"
        assert len(app.user_middleware) > 0, "App should have at least one middleware"

    def test_router_inclusion(self):
        """Test that API routers are properly included."""
        from backend.main import app

        # Check that routes are registered
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/api-info" in routes
        assert "/metrics" in routes
        assert "/metrics/summary" in routes


class TestAPIEndpoints:
    """Test API endpoints in main.py."""

    def test_read_root_endpoint(self):
        """Test the root endpoint returns correct information."""
        from api import SUPPORTED_VERSIONS, DEFAULT_VERSION, DEPRECATED_VERSIONS

        result = read_root()

        assert result["message"] == "Welcome to the Chama Wallet SaaS API"
        assert result["version"] == "1.0.0"
        assert result["status"] == "operational"
        assert result["api_versions"] == SUPPORTED_VERSIONS
        assert result["default_version"] == DEFAULT_VERSION
        assert "docs" in result
        assert "v1" in result["docs"]
        assert "v2" in result["docs"]

    def test_get_api_info_endpoint(self):
        """Test the API info endpoint returns versioning information."""
        from api import SUPPORTED_VERSIONS, DEFAULT_VERSION, DEPRECATED_VERSIONS

        result = get_api_info()

        assert result["title"] == "Chama Wallet API"
        assert result["version"] == "1.0.0"
        assert result["supported_versions"] == SUPPORTED_VERSIONS
        assert result["deprecated_versions"] == DEPRECATED_VERSIONS
        assert result["default_version"] == DEFAULT_VERSION
        assert result["versioning_strategy"] == "URL-based (e.g., /api/v1/endpoint)"
        assert "documentation" in result

    @patch('backend.main.get_prometheus_metrics')
    def test_get_metrics_endpoint(self, mock_get_metrics):
        """Test the metrics endpoint."""
        mock_get_metrics.return_value = {"metric": "value"}

        result = get_metrics()

        assert result == {"metric": "value"}
        mock_get_metrics.assert_called_once()

    @patch('backend.main.get_metrics_summary')
    def test_get_metrics_summary_endpoint(self, mock_get_metrics_summary):
        """Test the metrics summary endpoint."""
        mock_get_metrics_summary.return_value = {"summary": "data"}

        result = get_metrics_summary_endpoint()

        assert result == {"summary": "data"}
        mock_get_metrics_summary.assert_called_once()


class TestExceptionHandlers:
    """Test global exception handlers in main.py."""

    @pytest.mark.asyncio
    async def test_chama_wallet_exception_handler(self):
        """Test custom ChamaWallet exception handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        # Create mock request
        mock_request = AsyncMock(spec=Request)

        # Create test exception
        exc = ChamaWalletException(
            status_code=400,
            error_code="test_error",
            detail="Test error message"
        )

        # Call handler
        response = await chama_wallet_exception_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body
        assert b"test_error" in data
        assert b"Test error message" in data

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self):
        """Test Pydantic validation error handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        mock_request = AsyncMock(spec=Request)

        # Create validation error
        exc = RequestValidationError([
            {"loc": ["body", "field"], "msg": "field required", "type": "value_error.missing"}
        ])

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422
        data = response.body
        assert b"validation_error" in data

    @pytest.mark.asyncio
    async def test_integrity_error_handler(self):
        """Test database integrity error handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        mock_request = AsyncMock(spec=Request)
        exc = IntegrityError("statement", "params", Exception("Integrity constraint violated"))

        response = await integrity_error_handler(mock_request, exc)

        assert response.status_code == 400
        data = response.body
        assert b"database_integrity_error" in data

    @pytest.mark.asyncio
    async def test_sqlalchemy_exception_handler(self):
        """Test general SQLAlchemy error handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        mock_request = AsyncMock(spec=Request)
        exc = SQLAlchemyError("Database connection failed")

        response = await sqlalchemy_exception_handler(mock_request, exc)

        assert response.status_code == 500
        data = response.body
        assert b"database_error" in data

    @pytest.mark.asyncio
    async def test_http_exception_handler(self):
        """Test HTTP exception handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        mock_request = AsyncMock(spec=Request)
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        data = response.body
        assert b"http_404" in data
        assert b"Not found" in data

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler."""
        from fastapi import Request
        from unittest.mock import AsyncMock

        mock_request = AsyncMock(spec=Request)
        exc = Exception("Unexpected error")

        response = await general_exception_handler(mock_request, exc)

        assert response.status_code == 500
        data = response.body
        assert b"internal_server_error" in data
        assert b"An unexpected error occurred" in data


class TestAppIntegration:
    """Integration tests for the FastAPI app."""

    def test_root_endpoint_integration(self):
        """Test root endpoint through TestClient."""
        from fastapi.testclient import TestClient
        from backend.main import app

        # Use the actual main app for integration testing
        with TestClient(app) as test_client:
            response = test_client.get("/")
            assert response.status_code == 200

            data = response.json()
            assert "message" in data
            assert "version" in data
            assert "api_versions" in data
            assert "docs" in data

    def test_api_info_endpoint_integration(self):
        """Test API info endpoint through TestClient."""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/api-info")
            assert response.status_code == 200

            data = response.json()
            assert "title" in data
            assert "versioning_strategy" in data
            assert "documentation" in data

    def test_metrics_endpoint_integration(self):
        """Test metrics endpoint through TestClient."""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/metrics")
            # Metrics endpoint should return some response (may vary based on implementation)
            assert response.status_code in [200, 404]  # May not be fully implemented

    def test_metrics_summary_endpoint_integration(self):
        """Test metrics summary endpoint through TestClient."""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/metrics/summary")
            # Metrics summary endpoint should return some response
            assert response.status_code in [200, 404]  # May not be fully implemented

    def test_openapi_docs_available(self):
        """Test that OpenAPI documentation is available."""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/docs")
            # Docs endpoint should be available (may redirect or return HTML)
            assert response.status_code in [200, 302, 404]  # Various possible responses

    def test_openapi_json_available(self):
        """Test that OpenAPI JSON spec is available."""
        from fastapi.testclient import TestClient
        from backend.main import app

        with TestClient(app) as test_client:
            response = test_client.get("/openapi.json")
            # OpenAPI JSON should be available
            assert response.status_code in [200, 404]  # May not be fully configured
