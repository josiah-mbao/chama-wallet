"""
Comprehensive unit tests for middleware components.
Tests middleware functionality, request processing, and integration behavior.
"""
import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import Request, Response
from starlette.datastructures import URL


@pytest.fixture
def mock_app():
    """Mock FastAPI application for middleware testing"""
    app = MagicMock()
    app.return_value = Response(status_code=200)
    return app


@pytest.fixture
def mock_request():
    """Mock FastAPI request object"""
    request = MagicMock(spec=Request)
    request.method = "GET"
    # Create a proper mock URL with path attribute
    mock_url = MagicMock()
    mock_url.path = "/chamas/123/members"
    request.url = mock_url
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "test-agent"}
    return request


@pytest.fixture
def mock_response():
    """Mock FastAPI response object"""
    response = MagicMock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


class TestTenantContextMiddleware:
    """Test TenantContextMiddleware functionality"""

    @pytest.fixture
    def middleware(self, mock_app):
        from backend.middleware import TenantContextMiddleware
        return TenantContextMiddleware(mock_app)

    @pytest.mark.asyncio
    async def test_tenant_extraction_from_chama_route(self, middleware, mock_request):
        """Test tenant ID extraction from /chamas/{id}/ routes"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/456/contributions"
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            mock_tenant.set.return_value = "token_123"
            mock_response = Response(status_code=200)

            # Call dispatch
            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            # Verify tenant was extracted and set
            mock_tenant.set.assert_called_once_with(456)
            mock_start.assert_called_once_with(456)
            mock_end.assert_called_once_with("GET", "/chamas/456/contributions", 200)
            mock_tenant.reset.assert_called_once_with("token_123")

    @pytest.mark.asyncio
    async def test_tenant_extraction_from_versioned_chama_route(self, middleware, mock_request):
        """Test tenant ID extraction from /api/v1/chamas/{id}/ routes"""
        mock_url = MagicMock()
        mock_url.path = "/api/v1/chamas/789/members"
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            mock_tenant.set.return_value = "token_456"
            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            mock_tenant.set.assert_called_once_with(789)
            mock_start.assert_called_once_with(789)
            mock_end.assert_called_once_with("GET", "/api/v1/chamas/789/members", 200)
            mock_tenant.reset.assert_called_once_with("token_456")

    @pytest.mark.asyncio
    async def test_no_tenant_context_for_non_chama_routes(self, middleware, mock_request):
        """Test no tenant context for routes not involving chamas"""
        mock_url = MagicMock()
        mock_url.path = "/users/token"
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            # Verify tenant context was NOT set
            mock_tenant.set.assert_not_called()
            mock_start.assert_called_once_with()  # Called without tenant_id
            mock_end.assert_called_once_with("GET", "/users/token", 200)
            mock_tenant.reset.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_tenant_id_format(self, middleware, mock_request):
        """Test handling of invalid tenant ID formats"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/abc/contributions"  # Invalid ID
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            # Should not set tenant context for invalid ID
            mock_tenant.set.assert_not_called()
            mock_start.assert_called_once_with()
            mock_end.assert_called_once_with("GET", "/chamas/abc/contributions", 200)

    @pytest.mark.asyncio
    async def test_exception_handling_with_context_cleanup(self, middleware, mock_request):
        """Test proper context cleanup when exceptions occur"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/123/members"
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            mock_tenant.set.return_value = "token_789"
            async def failing_app(r):
                raise Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                await middleware.dispatch(mock_request, failing_app)

            # Verify context cleanup happened even with exception
            mock_tenant.set.assert_called_once_with(123)
            mock_tenant.reset.assert_called_once_with("token_789")
            mock_end.assert_called_once_with("GET", "/chamas/123/members", 500)

    @pytest.mark.asyncio
    async def test_exception_handling_without_tenant_context(self, middleware, mock_request):
        """Test exception handling for non-tenant routes"""
        mock_url = MagicMock()
        mock_url.path = "/users/login"
        mock_request.url = mock_url

        with patch('backend.middleware.current_tenant') as mock_tenant, \
             patch('backend.middleware.start_request_metrics') as mock_start, \
             patch('backend.middleware.end_request_metrics') as mock_end:

            async def failing_app(r):
                raise Exception("Test error")

            with pytest.raises(Exception, match="Test error"):
                await middleware.dispatch(mock_request, failing_app)

            mock_tenant.set.assert_not_called()
            mock_tenant.reset.assert_not_called()
            mock_end.assert_called_once_with("GET", "/users/login", 500)


class TestRequestLoggingMiddleware:
    """Test RequestLoggingMiddleware functionality"""

    @pytest.fixture
    def middleware(self, mock_app):
        from backend.middleware import RequestLoggingMiddleware
        return RequestLoggingMiddleware(mock_app)

    @pytest.mark.asyncio
    async def test_request_logging_normal_flow(self, middleware, mock_request, caplog):
        """Test normal request/response logging"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/123/summary"
        mock_request.url = mock_url

        with patch('backend.logging_config.get_request_correlation_id', return_value='corr-123'), \
             patch('time.time', side_effect=[1000.0, 1000.5]):  # 0.5s duration

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            # Check request log
            request_log = [r for r in caplog.records if "Request:" in r.message]
            assert len(request_log) == 1
            assert "GET /chamas/123/summary" in request_log[0].message
            assert "Client: 127.0.0.1" in request_log[0].message
            assert request_log[0].extra['correlation_id'] == 'corr-123'

            # Check response log
            response_log = [r for r in caplog.records if "Response:" in r.message]
            assert len(response_log) == 1
            assert "GET /chamas/123/summary" in response_log[0].message
            assert "Status: 200" in response_log[0].message
            assert "Duration: 0.5000s" in response_log[0].message

    @pytest.mark.asyncio
    async def test_excluded_paths_not_logged(self, middleware, mock_request, caplog):
        """Test that excluded paths are not logged"""
        mock_url = MagicMock()
        mock_url.path = "/docs"
        mock_request.url = mock_url

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        # Should not log anything for excluded paths
        logs = [r for r in caplog.records if r.name == "chama_wallet.requests"]
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_error_logging_on_exception(self, middleware, mock_request, caplog):
        """Test error logging when request processing fails"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/123/contributions"
        mock_request.url = mock_url

        with patch('backend.logging_config.get_request_correlation_id', return_value='corr-456'), \
             patch('time.time', side_effect=[1000.0, 1000.3]):

            async def failing_app(r):
                raise ValueError("Processing error")

            with pytest.raises(ValueError, match="Processing error"):
                await middleware.dispatch(mock_request, failing_app)

            # Check error log
            error_logs = [r for r in caplog.records if "Request failed:" in r.message]
            assert len(error_logs) == 1
            assert "GET /chamas/123/contributions" in error_logs[0].message
            assert "Processing error" in error_logs[0].message
            assert "Duration: 0.3000s" in error_logs[0].message
            assert error_logs[0].extra['correlation_id'] == 'corr-456'

    @pytest.mark.asyncio
    async def test_warning_log_for_error_responses(self, middleware, mock_request, caplog):
        """Test warning level logging for 4xx/5xx responses"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/999/summary"
        mock_request.url = mock_url

        with patch('backend.logging_config.get_request_correlation_id', return_value='corr-789'), \
             patch('time.time', side_effect=[1000.0, 1000.2]):

            mock_response = Response(status_code=404)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            response_logs = [r for r in caplog.records if "Response:" in r.message]
            assert len(response_logs) == 1
            assert response_logs[0].levelname == "WARNING"


class TestSecurityLoggingMiddleware:
    """Test SecurityLoggingMiddleware functionality"""

    @pytest.fixture
    def middleware(self, mock_app):
        from backend.middleware import SecurityLoggingMiddleware
        return SecurityLoggingMiddleware(mock_app)

    @pytest.mark.asyncio
    async def test_suspicious_user_agent_detection(self, middleware, mock_request, caplog):
        """Test detection of suspicious user agents"""
        mock_request.headers = {"user-agent": "sqlmap/1.0"}

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        security_logs = [r for r in caplog.records if "Security event detected" in r.message]
        assert len(security_logs) == 1
        assert "suspicious_user_agent" in security_logs[0].message
        assert "sqlmap" in security_logs[0].message

    @pytest.mark.asyncio
    async def test_multiple_suspicious_indicators(self, middleware, mock_request, caplog):
        """Test detection of multiple suspicious indicators"""
        # This would require multiple indicators, but currently only user-agent is checked
        # In a real implementation, this would test rate limiting, etc.
        mock_request.headers = {"user-agent": "nikto/2.0"}

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        security_logs = [r for r in caplog.records if "Security event detected" in r.message]
        assert len(security_logs) == 1
        assert "suspicious_user_agent" in security_logs[0].message

    @pytest.mark.asyncio
    async def test_normal_request_no_security_alert(self, middleware, mock_request, caplog):
        """Test that normal requests don't trigger security alerts"""
        mock_request.headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        security_logs = [r for r in caplog.records if "Security event detected" in r.message]
        assert len(security_logs) == 0


class TestPerformanceMonitoringMiddleware:
    """Test PerformanceMonitoringMiddleware functionality"""

    @pytest.fixture
    def middleware(self, mock_app):
        from backend.middleware import PerformanceMonitoringMiddleware
        return PerformanceMonitoringMiddleware(mock_app, slow_request_threshold=1.0)

    @pytest.mark.asyncio
    async def test_slow_request_detection(self, middleware, mock_request, caplog):
        """Test detection and logging of slow requests"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/123/analytics"
        mock_request.url = mock_url

        with patch('time.time', side_effect=[1000.0, 1002.5]):  # 2.5s duration (over threshold)

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            slow_logs = [r for r in caplog.records if "Slow request:" in r.message]
            assert len(slow_logs) == 1
            assert "GET /chamas/123/analytics" in slow_logs[0].message
            assert "Duration: 2.5000s" in slow_logs[0].message
            assert "Status: 200" in slow_logs[0].message

    @pytest.mark.asyncio
    async def test_fast_request_no_alert(self, middleware, mock_request, caplog):
        """Test that fast requests don't trigger alerts"""
        mock_url = MagicMock()
        mock_url.path = "/chamas/123/summary"
        mock_request.url = mock_url

        with patch('time.time', side_effect=[1000.0, 1000.5]):  # 0.5s duration (under threshold)

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            slow_logs = [r for r in caplog.records if "Slow request:" in r.message]
            assert len(slow_logs) == 0

    @pytest.mark.asyncio
    async def test_custom_threshold(self, mock_app, mock_request, caplog):
        """Test configurable slow request threshold"""
        from backend.middleware import PerformanceMonitoringMiddleware
        middleware = PerformanceMonitoringMiddleware(mock_app, slow_request_threshold=0.5)

        mock_url = MagicMock()
        mock_url.path = "/api/v1/chamas/456/members"
        mock_request.url = mock_url

        with patch('time.time', side_effect=[1000.0, 1000.8]):  # 0.8s duration (over custom threshold)

            mock_response = Response(status_code=200)

            async def mock_call_next(r):
                return mock_response

            result = await middleware.dispatch(mock_request, mock_call_next)

            slow_logs = [r for r in caplog.records if "Slow request:" in r.message]
            assert len(slow_logs) == 1
            assert "Duration: 0.8000s" in slow_logs[0].message


class TestAPIVersioningMiddleware:
    """Test APIVersioningMiddleware functionality"""

    @pytest.fixture
    def middleware(self, mock_app):
        from backend.middleware import APIVersioningMiddleware
        return APIVersioningMiddleware(mock_app)

    @pytest.mark.asyncio
    async def test_version_headers_for_v1_route(self, middleware, mock_request):
        """Test API versioning headers for v1 routes"""
        mock_url = MagicMock()
        mock_url.path = "/api/v1/chamas/123"
        mock_request.url = mock_url

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.headers["API-Version"] == "v1"
        assert "v1" in result.headers["API-Supported-Versions"]
        assert "v2" in result.headers["API-Supported-Versions"]
        assert result.headers["API-Deprecated-Versions"] == ""

    @pytest.mark.asyncio
    async def test_version_headers_for_v2_route(self, middleware, mock_request):
        """Test API versioning headers for v2 routes"""
        mock_url = MagicMock()
        mock_url.path = "/api/v2/users/profile"
        mock_request.url = mock_url

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.headers["API-Version"] == "v2"
        assert "v1" in result.headers["API-Supported-Versions"]
        assert "v2" in result.headers["API-Supported-Versions"]

    @pytest.mark.asyncio
    async def test_default_headers_for_non_versioned_routes(self, middleware, mock_request):
        """Test default headers for routes without version prefix"""
        mock_url = MagicMock()
        mock_url.path = "/health"
        mock_request.url = mock_url

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        assert result.headers["API-Version"] == "v1"  # Default version
        assert "v1" in result.headers["API-Supported-Versions"]
        assert "v2" in result.headers["API-Supported-Versions"]

    @pytest.mark.asyncio
    async def test_invalid_version_handling(self, middleware, mock_request):
        """Test handling of invalid API version formats"""
        mock_url = MagicMock()
        mock_url.path = "/api/v3/endpoint"  # Invalid version
        mock_request.url = mock_url

        mock_response = Response(status_code=200)

        async def mock_call_next(r):
            return mock_response

        result = await middleware.dispatch(mock_request, mock_call_next)

        # Should fall back to default headers
        assert result.headers["API-Version"] == "v1"
        assert "v1" in result.headers["API-Supported-Versions"]
        assert "v2" in result.headers["API-Supported-Versions"]
