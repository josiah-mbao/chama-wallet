# backend/rate_limiting.py
import time
import asyncio
import re
from collections import defaultdict, deque
from typing import Optional, Dict, Tuple
import logging

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from backend.metrics import record_rate_limit_violation


class InMemoryRateLimiter:
    """Simple in-memory rate limiter for development/single-instance deployment"""

    def __init__(self):
        self.requests = defaultdict(lambda: deque(maxlen=1000))

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed: bool, retry_after: float)
        """
        now = time.time()
        request_times = self.requests[key]

        # Remove old requests outside the window
        while request_times and request_times[0] < now - window_seconds:
            request_times.popleft()

        # Check if under limit
        if len(request_times) < max_requests:
            request_times.append(now)
            return True, 0.0

        # Calculate retry time
        oldest_allowed = request_times[0] + window_seconds
        retry_after = oldest_allowed - now

        return False, max(0, retry_after)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting"""

    def __init__(
        self,
        app,
        limiter=None,
        global_limits: Optional[Dict[str, int]] = None,
        endpoint_limits: Optional[Dict[str, Tuple[int, int]]] = None,  # path -> (max_requests, window_seconds)
        exempt_paths: Optional[list] = None,
        exempt_ips: Optional[list] = None
    ):
        super().__init__(app)
        self.limiter = limiter or InMemoryRateLimiter()
        self.logger = logging.getLogger("chama_wallet.rate_limiting")

        # Default global limits (requests per window)
        self.global_limits = global_limits or {
            "default": (100, 60),  # 100 requests per minute
            "authenticated": (500, 60),  # 500 requests per minute for logged-in users
            "strict": (10, 60),   # 10 requests per minute for sensitive endpoints
        }

        # Endpoint-specific limits
        self.endpoint_limits = endpoint_limits or {
            "/users/token": ("strict", None),  # Login endpoint - strict limits
            "/docs": ("default", None),        # API docs - normal limits
            "/openapi.json": ("default", None), # OpenAPI spec - normal limits
            "/favicon.ico": ("default", None),  # Favicon - normal limits
            "/": ("default", None),            # Health check - normal limits
        }

        # Exempt paths (no rate limiting)
        self.exempt_paths = set(exempt_paths or ["/health", "/metrics"])

        # Exempt IPs (for monitoring, admins, etc.)
        self.exempt_ips = set(exempt_ips or [])

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for tests (can be controlled via environment variable)
        import os
        if os.getenv("DISABLE_RATE_LIMITING") == "true":
            return await call_next(request)

        # Skip rate limiting for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Get client identifier
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        # Skip rate limiting for exempt IPs
        if client_ip in self.exempt_ips:
            return await call_next(request)

        # Determine which rate limit to apply
        limit_name, custom_limit = self._get_rate_limit_config(request.url.path)

        # Use custom limit if specified for this endpoint
        if custom_limit:
            max_requests, window_seconds = custom_limit
        else:
            max_requests, window_seconds = self.global_limits[limit_name]

        # Create tenant-aware rate limit key
        chama_id = self._get_chama_id(request.url.path)

        if chama_id is not None:
            # For chama-specific endpoints, include tenant in rate limit key
            # This ensures each chama gets its own rate limit quota
            if user_id:
                # User within a specific chama: user:123@chama:456
                rate_limit_key = f"{user_id}@chama:{chama_id}"
            else:
                # Anonymous user for a chama: ip:1.2.3.4@chama:456
                rate_limit_key = f"ip:{client_ip}@chama:{chama_id}"
        else:
            # For non-chama endpoints (global operations like user auth, health checks)
            # Use the original global rate limiting
            rate_limit_key = user_id if user_id else f"ip:{client_ip}"

        # Check rate limit
        is_allowed, retry_after = self.limiter.is_allowed(
            rate_limit_key, max_requests, window_seconds
        )

        if not is_allowed:
            # Record rate limit violation in metrics
            record_rate_limit_violation("request_rate_limit")

            # Log rate limit violation with tenant information
            tenant_info = f" [TENANT: {chama_id}]" if chama_id else " [GLOBAL]"
            self.logger.warning(
                f"Rate limit exceeded: {rate_limit_key} - Path: {request.method} {request.url.path}{tenant_info} - "
                f"Limit: {max_requests}/{window_seconds}s - Retry after: {retry_after:.1f}s",
                extra={"correlation_id": getattr(request.state, "correlation_id", "unknown")}
            )

            # Return rate limit exceeded response
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after:.1f} seconds.",
                headers={"Retry-After": str(int(retry_after))}
            )

        # Add rate limit info to response headers for clients
        response = await call_next(request)

        # Add rate limit headers (RFC 6585)
        remaining_requests = max(0, max_requests - len(self.limiter.requests[rate_limit_key]))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window_seconds))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address, handling proxies"""
        # Check for forwarded headers (common in production with load balancers)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check other proxy headers
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct connection
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request context if available"""
        # This would be set by auth middleware - we'll check for it
        # For now, we'll look at request state or auth context if available
        try:
            # FastAPI auth dependency might have set user in request.state
            if hasattr(request.state, "user") and request.state.user:
                return f"user:{request.state.user.id}"
        except AttributeError:
            pass

        return None

    def _get_chama_id(self, path: str) -> Optional[int]:
        """Extract chama_id from tenant-aware URL paths"""
        # Regex patterns for extracting chama_id from URLs
        # This mirrors the patterns used in TenantContextMiddleware
        chama_patterns = [
            re.compile(r'/chamas/(\d+)/?.*'),  # /chamas/{id}/...
        ]

        for pattern in chama_patterns:
            match = pattern.match(path)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        return None

    def _get_rate_limit_config(self, path: str) -> Tuple[str, Optional[Tuple[int, int]]]:
        """
        Determine rate limit configuration for a path.
        Returns (limit_name, custom_limit) where custom_limit is (max_requests, window_seconds)
        """
        # Check for exact path match
        if path in self.endpoint_limits:
            limit_name, custom_limit = self.endpoint_limits[path]
            return limit_name, custom_limit

        # Check for pattern matches (e.g., /users/123 -> /users/*)
        for pattern, config in self.endpoint_limits.items():
            if pattern.endswith("/*"):
                base_path = pattern[:-2]
                if path.startswith(base_path):
                    limit_name, custom_limit = config
                    return limit_name, custom_limit

        # Default to "authenticated" for /users/* and /chamas/*, "default" for others
        if path.startswith(("/users/", "/chamas/")):
            return ("authenticated", None)

        return ("default", None)


# Test function for rate limiting
async def test_rate_limiting():
    """Test function to verify rate limiting works"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, global_limits={"test": (3, 10)})

    @app.get("/test")
    async def test_endpoint():
        return {"message": "ok"}

    client = TestClient(app)

    # This should work
    for i in range(3):
        response = client.get("/test")
        assert response.status_code == 200
        print(f"Request {i+1}: OK")

    # This should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    print("Request 4: Rate limited (429)")

    print("✅ Rate limiting test passed!")


if __name__ == "__main__":
    asyncio.run(test_rate_limiting())
