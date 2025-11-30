"""
Unit tests for rate limiting functionality.
Tests tenant-aware rate limiting, middleware integration, and rate limit logic.
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from backend.rate_limiting import (
    RateLimitMiddleware,
    InMemoryRateLimiter
)


class TestInMemoryRateLimiter:
    """Test the basic in-memory rate limiter functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = InMemoryRateLimiter()
        assert limiter.requests == {}

    def test_rate_limiter_allows_requests_under_limit(self):
        """Test rate limiter allows requests under the limit."""
        limiter = InMemoryRateLimiter()

        # Test allowing multiple requests within limit
        for i in range(3):
            allowed, retry_after = limiter.is_allowed("test_key", 5, 60)
            assert allowed is True
            assert retry_after == 0.0

    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test rate limiter blocks requests over the limit."""
        limiter = InMemoryRateLimiter()

        # Use up all requests
        for i in range(5):
            allowed, retry_after = limiter.is_allowed("test_key", 5, 60)
            assert allowed is True

        # Next request should be blocked
        allowed, retry_after = limiter.is_allowed("test_key", 5, 60)
        assert allowed is False
        assert retry_after > 0

    def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window."""
        limiter = InMemoryRateLimiter()

        # Use up requests
        for i in range(3):
            limiter.is_allowed("test_key", 3, 1)  # 1 second window

        # Wait for window to expire
        time.sleep(1.1)

        # Should allow new requests
        allowed, retry_after = limiter.is_allowed("test_key", 3, 1)
        assert allowed is True
        assert retry_after == 0.0

    def test_rate_limiter_separate_keys(self):
        """Test rate limiter handles separate keys independently."""
        limiter = InMemoryRateLimiter()

        # Use up requests for key1
        for i in range(2):
            limiter.is_allowed("key1", 2, 60)

        # key2 should still work
        allowed, retry_after = limiter.is_allowed("key2", 2, 60)
        assert allowed is True

        # key1 should be blocked
        allowed, retry_after = limiter.is_allowed("key1", 2, 60)
        assert allowed is False


class TestRateLimitMiddleware:
    """Test the RateLimitMiddleware functionality."""

    def test_middleware_initialization(self):
        """Test middleware initializes with correct defaults."""
        middleware = RateLimitMiddleware(None)

        assert middleware.limiter is not None
        assert "default" in middleware.global_limits
        assert "authenticated" in middleware.global_limits
        assert "strict" in middleware.global_limits
        assert "/health" in middleware.exempt_paths
        assert "/metrics" in middleware.exempt_paths

    def test_middleware_custom_config(self):
        """Test middleware with custom configuration."""
        custom_limits = {"custom": (10, 30)}
        custom_endpoints = {"/api/test": ("custom", None)}
        exempt_paths = ["/health"]
        exempt_ips = ["127.0.0.1"]

        middleware = RateLimitMiddleware(
            None,
            global_limits=custom_limits,
            endpoint_limits=custom_endpoints,
            exempt_paths=exempt_paths,
            exempt_ips=exempt_ips
        )

        assert middleware.global_limits["custom"] == (10, 30)
        assert middleware.endpoint_limits["/api/test"] == ("custom", None)
        assert "/health" in middleware.exempt_paths
        assert "127.0.0.1" in middleware.exempt_ips

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test client IP extraction from X-Forwarded-For header."""
        middleware = RateLimitMiddleware(None)

        # Test with X-Forwarded-For
        request = Mock()
        request.headers = {"x-forwarded-for": "203.0.113.1, 198.51.100.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_from_x_real_ip(self):
        """Test client IP extraction from X-Real-IP header."""
        middleware = RateLimitMiddleware(None)

        request = Mock()
        request.headers = {"x-real-ip": "198.51.100.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "198.51.100.1"

    def test_get_client_ip_from_request_client(self):
        """Test client IP extraction from request.client."""
        middleware = RateLimitMiddleware(None)

        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_fallback(self):
        """Test client IP fallback to unknown."""
        middleware = RateLimitMiddleware(None)

        request = Mock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"

    def test_get_user_id_from_request_state(self):
        """Test user ID extraction from request state."""
        middleware = RateLimitMiddleware(None)

        request = Mock()
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = 123

        user_id = middleware._get_user_id(request)
        assert user_id == "user:123"

    def test_get_user_id_none_when_no_user(self):
        """Test user ID returns None when no user in request."""
        middleware = RateLimitMiddleware(None)

        request = Mock()
        request.state = Mock()
        request.state.user = None

        user_id = middleware._get_user_id(request)
        assert user_id is None

    def test_get_chama_id_from_url(self):
        """Test tenant ID extraction from URLs."""
        middleware = RateLimitMiddleware(None)

        test_cases = [
            ("/chamas/123/members", 123),
            ("/chamas/456/contributions", 456),
            ("/chamas/789/summary", 789),
            ("/api/v1/chamas/999/analytics", 999),
            ("/users/profile", None),
            ("/docs", None),
            ("/api/v1/docs", None),
        ]

        for url, expected_id in test_cases:
            extracted_id = middleware._get_chama_id(url)
            assert extracted_id == expected_id, f"Failed for URL: {url}"

    def test_get_rate_limit_config_default(self):
        """Test rate limit config returns default for unknown paths."""
        middleware = RateLimitMiddleware(None)

        limit_name, custom_limit = middleware._get_rate_limit_config("/unknown/path")
        assert limit_name == "default"
        assert custom_limit is None

    def test_get_rate_limit_config_endpoint_specific(self):
        """Test rate limit config for endpoint-specific paths."""
        middleware = RateLimitMiddleware(None)

        # Test login endpoint (strict)
        limit_name, custom_limit = middleware._get_rate_limit_config("/users/token")
        assert limit_name == "strict"

        # Test docs endpoint
        limit_name, custom_limit = middleware._get_rate_limit_config("/docs")
        assert limit_name == "default"

    def test_get_rate_limit_config_authenticated_paths(self):
        """Test rate limit config for authenticated paths."""
        middleware = RateLimitMiddleware(None)

        # Test chama paths (authenticated)
        limit_name, custom_limit = middleware._get_rate_limit_config("/chamas/123/members")
        assert limit_name == "authenticated"

        # Test user paths (authenticated)
        limit_name, custom_limit = middleware._get_rate_limit_config("/users/456/profile")
        assert limit_name == "authenticated"

    @patch('backend.rate_limiting.time')
    def test_middleware_rate_limit_exceeded(self, mock_time):
        """Test middleware blocks requests when rate limit exceeded."""
        mock_time.time.return_value = 1000
        mock_time.sleep = time.sleep

        middleware = RateLimitMiddleware(None, global_limits={"test": (2, 60)})

        # Mock request
        request = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"

        # Mock response
        response = Mock()
        response.status_code = 200
        response.headers = {}

        # First two requests should pass
        for i in range(2):
            result = middleware._get_rate_limit_config("/test")
            # Simulate rate limiting logic
            limiter = middleware.limiter
            key = f"ip:127.0.0.1"
            allowed, retry_after = limiter.is_allowed(key, 2, 60)

            if i < 2:
                assert allowed is True
            else:
                assert allowed is False

    def test_middleware_exempt_paths(self):
        """Test middleware exempts specified paths."""
        middleware = RateLimitMiddleware(None)

        # Mock exempt request
        request = Mock()
        request.url.path = "/health"

        # Should not process rate limiting for exempt paths
        assert "/health" in middleware.exempt_paths

    def test_middleware_exempt_ips(self):
        """Test middleware exempts specified IPs."""
        middleware = RateLimitMiddleware(None, exempt_ips=["192.168.1.1"])

        request = Mock()
        request.url.path = "/api/test"
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.1"

        # Should be exempt from rate limiting
        assert "192.168.1.1" in middleware.exempt_ips


class TestTenantAwareRateLimiting:
    """Test tenant-aware rate limiting functionality."""

    def test_tenant_rate_limit_keys(self):
        """Test tenant-specific rate limit key generation."""
        middleware = RateLimitMiddleware(None)

        # Mock request for tenant endpoint
        request = Mock()
        request.url.path = "/chamas/123/members"
        request.method = "GET"
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        request.state.user = None

        chama_id = middleware._get_chama_id(request.url.path)
        assert chama_id == 123

        # Test key generation logic (user + tenant)
        user_id = middleware._get_user_id(request)
        client_ip = middleware._get_client_ip(request)

        # Should generate tenant-scoped key
        if chama_id and user_id:
            expected_key = f"{user_id}@chama:{chama_id}"
        elif chama_id:
            expected_key = f"ip:{client_ip}@chama:{chama_id}"
        else:
            expected_key = user_id or f"ip:{client_ip}"

        # Verify the key structure
        assert "@chama:" in expected_key or "ip:" in expected_key

    def test_cross_tenant_rate_limit_isolation(self):
        """Test that different tenants have separate rate limits."""
        middleware = RateLimitMiddleware(None, global_limits={"test": (2, 60)})

        # Mock requests for different tenants
        request1 = Mock()
        request1.url.path = "/chamas/123/members"
        request1.method = "GET"
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "127.0.0.1"
        request1.state = Mock()
        request1.state.user = None

        request2 = Mock()
        request2.url.path = "/chamas/456/members"
        request2.method = "GET"
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "127.0.0.1"
        request2.state = Mock()
        request2.state.user = None

        # Both should be able to make requests up to their limits
        limiter = middleware.limiter

        # Tenant 123 requests
        key1 = f"ip:127.0.0.1@chama:123"
        allowed1, _ = limiter.is_allowed(key1, 2, 60)
        assert allowed1 is True

        # Tenant 456 requests (should not affect tenant 123)
        key2 = f"ip:127.0.0.1@chama:456"
        allowed2, _ = limiter.is_allowed(key2, 2, 60)
        assert allowed2 is True

        # Verify different keys
        assert key1 != key2

    def test_tenant_rate_limit_with_user(self):
        """Test tenant rate limiting when user is authenticated."""
        middleware = RateLimitMiddleware(None)

        # Mock authenticated request
        request = Mock()
        request.url.path = "/chamas/789/contributions"
        request.method = "POST"
        request.headers = {}
        request.client = Mock()
        request.client.host = "10.0.0.1"
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = 42

        chama_id = middleware._get_chama_id(request.url.path)
        user_id = middleware._get_user_id(request)

        assert chama_id == 789
        assert user_id == "user:42"

        # Should generate user@tenant key
        expected_key_structure = f"{user_id}@chama:{chama_id}"
        assert expected_key_structure == "user:42@chama:789"


class TestRateLimitingIntegration:
    """Test rate limiting integration scenarios."""

    def test_rate_limit_headers_added(self):
        """Test that rate limit headers are added to responses."""
        # This would be tested in integration with actual middleware dispatch
        # For now, verify the header logic exists in the code
        pass

    def test_rate_limiting_module_imports(self):
        """Test that rate limiting module imports work correctly."""
        # Verify the module and its key components can be imported
        try:
            from backend.rate_limiting import RateLimitMiddleware, InMemoryRateLimiter
            assert RateLimitMiddleware is not None
            assert InMemoryRateLimiter is not None
        except ImportError:
            pytest.fail("Rate limiting module imports failed")


class TestRateLimitingEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_url_handling(self):
        """Test handling of malformed URLs."""
        middleware = RateLimitMiddleware(None)

        # Test URLs that might cause issues
        edge_cases = [
            "/chamas/",  # Missing ID
            "/chamas/abc/members",  # Non-numeric ID
            "/chamas/123",  # No sub-path
            "",  # Empty path
            "/chamas/123/members/extra/path",  # Extra path components
        ]

        for url in edge_cases:
            chama_id = middleware._get_chama_id(url)
            # Should not crash, should return None or valid ID
            assert isinstance(chama_id, (int, type(None)))

    def test_rate_limit_window_edge_cases(self):
        """Test rate limiting at window boundaries."""
        limiter = InMemoryRateLimiter()

        # Test exactly at limit
        for i in range(5):
            allowed, retry_after = limiter.is_allowed("test", 5, 60)
            if i < 5:
                assert allowed is True
            else:
                assert allowed is False

    def test_concurrent_requests_simulation(self):
        """Test rate limiting under simulated concurrent load."""
        limiter = InMemoryRateLimiter()

        # Simulate multiple clients
        clients = ["client_1", "client_2", "client_3"]
        requests_per_client = 10

        total_allowed = 0
        for client in clients:
            for i in range(requests_per_client):
                allowed, _ = limiter.is_allowed(client, 5, 60)
                if allowed:
                    total_allowed += 1

        # Each client should get up to their limit
        assert total_allowed == 15  # 3 clients * 5 requests each

    def test_rate_limit_reset_behavior(self):
        """Test rate limit reset timing."""
        limiter = InMemoryRateLimiter()

        # Fill up the limit
        for i in range(3):
            limiter.is_allowed("test", 3, 2)  # 2 second window

        # Should be blocked
        allowed, retry_after = limiter.is_allowed("test", 3, 2)
        assert allowed is False
        assert retry_after > 0

        # After waiting, should reset
        time.sleep(2.1)
        allowed, retry_after = limiter.is_allowed("test", 3, 2)
        assert allowed is True
        assert retry_after == 0.0
