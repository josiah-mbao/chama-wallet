"""
Enhanced unit tests for rate limiting functionality.
"""
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient
from backend.rate_limiting import (
    InMemoryRateLimiter,
    RateLimitMiddleware
)


@pytest.fixture
def mock_request():
    """Mock FastAPI request object."""
    request = Mock()
    request.url.path = "/test"
    request.method = "GET"
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    request.state = Mock()
    return request


@pytest.fixture
def rate_limiter():
    """Fresh InMemoryRateLimiter instance."""
    return InMemoryRateLimiter()


@pytest.fixture
def rate_limit_middleware():
    """RateLimitMiddleware instance with test configuration."""
    return RateLimitMiddleware(
        app=Mock(),
        global_limits={
            "default": (10, 60),
            "authenticated": (50, 60),
            "strict": (5, 60),
        },
        exempt_paths=["/health"],
        exempt_ips=["127.0.0.1"]
    )


class TestInMemoryRateLimiter:
    """Test InMemoryRateLimiter functionality."""

    def test_initialization(self, rate_limiter):
        """Test rate limiter initializes with empty requests."""
        assert rate_limiter.requests == {}

    def test_allow_under_limit(self, rate_limiter):
        """Test requests under limit are allowed."""
        key = "test_key"
        max_requests = 5
        window_seconds = 60

        # Make requests under the limit
        for i in range(max_requests):
            allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
            assert allowed is True
            assert retry_after == 0.0

        # Check that requests are tracked
        assert len(rate_limiter.requests[key]) == max_requests

    def test_block_over_limit(self, rate_limiter):
        """Test requests over limit are blocked."""
        key = "test_key"
        max_requests = 3
        window_seconds = 60

        # Fill up the limit
        for i in range(max_requests):
            allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
            assert allowed is True

        # Next request should be blocked
        allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
        assert allowed is False
        assert retry_after > 0

    def test_window_cleanup(self, rate_limiter):
        """Test old requests are cleaned up from sliding window."""
        key = "test_key"
        max_requests = 2
        window_seconds = 1  # Very short window

        # Make initial requests
        rate_limiter.is_allowed(key, max_requests, window_seconds)
        rate_limiter.is_allowed(key, max_requests, window_seconds)

        # Wait for window to expire
        time.sleep(1.1)

        # New request should be allowed (old ones cleaned up)
        allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
        assert allowed is True

    def test_different_keys_isolation(self, rate_limiter):
        """Test different keys are isolated."""
        key1 = "user:123"
        key2 = "user:456"
        max_requests = 2
        window_seconds = 60

        # Fill up key1
        rate_limiter.is_allowed(key1, max_requests, window_seconds)
        rate_limiter.is_allowed(key1, max_requests, window_seconds)

        # key2 should still be allowed
        allowed, retry_after = rate_limiter.is_allowed(key2, max_requests, window_seconds)
        assert allowed is True

    def test_retry_after_calculation(self, rate_limiter):
        """Test retry_after is calculated correctly."""
        key = "test_key"
        max_requests = 2
        window_seconds = 10

        # Fill the limit
        rate_limiter.is_allowed(key, max_requests, window_seconds)
        rate_limiter.is_allowed(key, max_requests, window_seconds)

        # Next request should calculate retry time
        allowed, retry_after = rate_limiter.is_allowed(key, max_requests, window_seconds)
        assert allowed is False
        assert 0 < retry_after <= window_seconds


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""

    @pytest.mark.asyncio
    async def test_exempt_paths_skip_limiting(self, rate_limit_middleware, mock_request):
        """Test exempt paths skip rate limiting."""
        mock_request.url.path = "/health"

        # Mock the limiter to ensure it's not called
        rate_limit_middleware.limiter.is_allowed = Mock()

        # Call middleware
        result = await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        # Limiter should not be checked
        rate_limit_middleware.limiter.is_allowed.assert_not_called()

    @pytest.mark.asyncio
    async def test_exempt_ips_skip_limiting(self, rate_limit_middleware, mock_request):
        """Test exempt IPs skip rate limiting."""
        mock_request.url.path = "/api/test"
        mock_request.client.host = "127.0.0.1"

        rate_limit_middleware.limiter.is_allowed = Mock()

        result = await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        rate_limit_middleware.limiter.is_allowed.assert_not_called()

    @pytest.mark.asyncio
    async def test_disable_rate_limiting_env_var(self, rate_limit_middleware, mock_request):
        """Test DISABLE_RATE_LIMITING environment variable."""
        mock_request.url.path = "/api/test"

        with patch('os.getenv', return_value='true'):
            rate_limit_middleware.limiter.is_allowed = Mock()
            result = await rate_limit_middleware.dispatch(mock_request, AsyncMock())
            rate_limit_middleware.limiter.is_allowed.assert_not_called()

    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, rate_limit_middleware, mock_request):
        """Test allowed requests pass through."""
        mock_request.url.path = "/api/test"

        # Mock limiter to allow request
        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(True, 0.0))

        mock_call_next = AsyncMock()
        mock_response = Mock()
        mock_call_next.return_value = mock_response

        result = await rate_limit_middleware.dispatch(mock_request, mock_call_next)

        # Should call next handler
        mock_call_next.assert_called_once()
        # Should return the response
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_rate_limit_blocked(self, rate_limit_middleware, mock_request):
        """Test blocked requests raise HTTPException."""
        mock_request.url.path = "/api/test"

        # Mock limiter to block request
        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(False, 5.5))

        with patch('backend.rate_limiting.record_rate_limit_violation') as mock_record:
            with pytest.raises(HTTPException) as exc_info:
                await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        # Should raise 429 error
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded" in exc_info.value.detail
        # Should record violation
        mock_record.assert_called_once()

    def test_client_ip_extraction_direct(self, rate_limit_middleware, mock_request):
        """Test client IP extraction from direct connection."""
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}

        ip = rate_limit_middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_client_ip_extraction_x_forwarded_for(self, rate_limit_middleware, mock_request):
        """Test client IP extraction from X-Forwarded-For header."""
        mock_request.headers = {"x-forwarded-for": "203.0.113.1, 198.51.100.1"}
        mock_request.client = None

        ip = rate_limit_middleware._get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_client_ip_extraction_x_real_ip(self, rate_limit_middleware, mock_request):
        """Test client IP extraction from X-Real-IP header."""
        mock_request.headers = {"x-real-ip": "203.0.113.1"}
        mock_request.client = None

        ip = rate_limit_middleware._get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_client_ip_extraction_unknown(self, rate_limit_middleware, mock_request):
        """Test client IP fallback to unknown."""
        mock_request.client = None
        mock_request.headers = {}

        ip = rate_limit_middleware._get_client_ip(mock_request)
        assert ip == "unknown"

    def test_user_id_extraction_from_state(self, rate_limit_middleware, mock_request):
        """Test user ID extraction from request state."""
        mock_user = Mock()
        mock_user.id = 123
        mock_request.state.user = mock_user

        user_id = rate_limit_middleware._get_user_id(mock_request)
        assert user_id == "user:123"

    def test_user_id_extraction_none(self, rate_limit_middleware, mock_request):
        """Test user ID returns None when not available."""
        mock_request.state.user = None

        user_id = rate_limit_middleware._get_user_id(mock_request)
        assert user_id is None

    def test_chama_id_extraction_from_path(self, rate_limit_middleware):
        """Test chama ID extraction from various URL patterns."""
        test_cases = [
            ("/chamas/123/contributions", 123),
            ("/api/v1/chamas/456/members", 456),
            ("/api/v2/chamas/789/analytics", 789),
            ("/users/token", None),
            ("/health", None),
        ]

        for path, expected in test_cases:
            chama_id = rate_limit_middleware._get_chama_id(path)
            assert chama_id == expected, f"Failed for path: {path}"

    def test_rate_limit_config_default(self, rate_limit_middleware):
        """Test default rate limit configuration."""
        test_cases = [
            ("/unknown/path", ("default", None)),
            ("/health", ("default", None)),  # Would be exempt but still returns config
            ("/docs", ("default", None)),
        ]

        for path, expected in test_cases:
            config = rate_limit_middleware._get_rate_limit_config(path)
            assert config == expected

    def test_rate_limit_config_authenticated_endpoints(self, rate_limit_middleware):
        """Test authenticated endpoints get correct config."""
        test_cases = [
            ("/users/profile", ("authenticated", None)),
            ("/chamas/123/contributions", ("authenticated", None)),
        ]

        for path, expected in test_cases:
            config = rate_limit_middleware._get_rate_limit_config(path)
            assert config == expected

    def test_rate_limit_config_strict_endpoints(self, rate_limit_middleware):
        """Test strict endpoints get correct config."""
        config = rate_limit_middleware._get_rate_limit_config("/users/token")
        assert config[0] == "strict"

    def test_rate_limit_config_custom_endpoints(self, rate_limit_middleware):
        """Test custom endpoint configurations."""
        # Add custom config
        rate_limit_middleware.endpoint_limits["/custom"] = ("authenticated", (20, 30))

        config = rate_limit_middleware._get_rate_limit_config("/custom")
        assert config == ("authenticated", (20, 30))


class TestTenantAwareRateLimiting:
    """Test tenant-aware rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_tenant_aware_key_generation_user(self, rate_limit_middleware, mock_request):
        """Test rate limit key includes tenant for authenticated users."""
        mock_request.url.path = "/chamas/123/contributions"

        # Mock user
        mock_user = Mock()
        mock_user.id = 456
        mock_request.state.user = mock_user

        # Mock limiter
        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(True, 0.0))

        await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        # Should generate tenant-aware key
        rate_limit_middleware.limiter.is_allowed.assert_called_once()
        call_args = rate_limit_middleware.limiter.is_allowed.call_args
        assert call_args[0][0] == "user:456@chama:123"

    @pytest.mark.asyncio
    async def test_tenant_aware_key_generation_anonymous(self, rate_limit_middleware, mock_request):
        """Test rate limit key includes tenant for anonymous users."""
        mock_request.url.path = "/chamas/123/contributions"
        mock_request.client.host = "192.168.1.100"
        mock_request.state.user = None

        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(True, 0.0))

        await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        call_args = rate_limit_middleware.limiter.is_allowed.call_args
        assert call_args[0][0] == "ip:192.168.1.100@chama:123"

    @pytest.mark.asyncio
    async def test_global_key_generation(self, rate_limit_middleware, mock_request):
        """Test global rate limit keys for non-tenant endpoints."""
        mock_request.url.path = "/users/token"
        mock_request.client.host = "192.168.1.100"
        mock_request.state.user = None

        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(True, 0.0))

        await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        call_args = rate_limit_middleware.limiter.is_allowed.call_args
        assert call_args[0][0] == "ip:192.168.1.100"


class TestRateLimitResponseHeaders:
    """Test rate limit response header functionality."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_added(self, rate_limit_middleware, mock_request):
        """Test rate limit headers are added to responses."""
        mock_request.url.path = "/api/test"
        mock_request.client.host = "192.168.1.100"

        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(True, 0.0))

        mock_response = Mock()
        mock_response.headers = {}

        mock_call_next = AsyncMock(return_value=mock_response)

        result = await rate_limit_middleware.dispatch(mock_request, mock_call_next)

        # Check rate limit headers are added
        assert "X-RateLimit-Limit" in mock_response.headers
        assert "X-RateLimit-Remaining" in mock_response.headers
        assert "X-RateLimit-Reset" in mock_response.headers

    @pytest.mark.asyncio
    async def test_retry_after_header_on_block(self, rate_limit_middleware, mock_request):
        """Test Retry-After header is set on rate limit blocks."""
        mock_request.url.path = "/api/test"

        rate_limit_middleware.limiter.is_allowed = Mock(return_value=(False, 5.5))

        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_middleware.dispatch(mock_request, AsyncMock())

        # Check Retry-After header
        assert "Retry-After" in exc_info.value.headers
        assert exc_info.value.headers["Retry-After"] == "5"


class TestRateLimitingIntegration:
    """Integration tests for rate limiting end-to-end."""

    def test_middleware_initialization(self):
        """Test middleware initializes with correct defaults."""
        middleware = RateLimitMiddleware(app=Mock())

        assert "default" in middleware.global_limits
        assert "authenticated" in middleware.global_limits
        assert "strict" in middleware.global_limits
        assert "/health" in middleware.exempt_paths
        assert middleware.exempt_ips == set()

    def test_custom_configuration(self):
        """Test middleware accepts custom configuration."""
        custom_limits = {"custom": (25, 30)}
        custom_endpoints = {"/special": ("custom", None)}
        exempt_paths = ["/special", "/admin"]
        exempt_ips = ["192.168.1.1"]

        middleware = RateLimitMiddleware(
            app=Mock(),
            global_limits=custom_limits,
            endpoint_limits=custom_endpoints,
            exempt_paths=exempt_paths,
            exempt_ips=exempt_ips
        )

        assert middleware.global_limits["custom"] == (25, 30)
        assert middleware.endpoint_limits["/special"] == ("custom", None)
        assert "/special" in middleware.exempt_paths
        assert "/admin" in middleware.exempt_paths
        assert "192.168.1.1" in middleware.exempt_ips

    @pytest.mark.asyncio
    async def test_concurrent_requests_isolation(self, rate_limit_middleware):
        """Test concurrent requests are properly isolated."""
        # This would require more complex async testing
        # For now, test that different keys don't interfere
        limiter = rate_limit_middleware.limiter

        # User 1 makes requests
        for i in range(3):
            allowed, _ = limiter.is_allowed("user:1", 5, 60)
            assert allowed

        # User 2 should not be affected
        allowed, _ = limiter.is_allowed("user:2", 5, 60)
        assert allowed

        # User 1 hits limit
        allowed, retry_after = limiter.is_allowed("user:1", 5, 60)
        assert not allowed


@pytest.mark.asyncio
async def test_rate_limiting_integration():
    """Integration test for the complete rate limiting system."""
    # This mirrors the test_rate_limiting function in the module
    from fastapi import FastAPI

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, global_limits={"test": (3, 10)})

    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    # Should allow first 3 requests
    for i in range(3):
        response = client.get("/test")
        assert response.status_code == 200

    # Should block 4th request
    response = client.get("/test")
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]
    assert "Retry-After" in response.headers
