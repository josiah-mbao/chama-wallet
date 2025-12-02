"""
Middleware for HTTPS enforcement, security headers, and request processing.
"""
import time
import logging
import re
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.requests import Request as StarletteRequest
from backend.config import settings
from backend.logging_config import get_request_correlation_id
from backend.database import current_tenant
from backend.metrics import start_request_metrics, end_request_metrics


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS in production.
    """

    async def dispatch(self, request: Request, call_next):
        # Check if HTTPS redirect is enabled
        if settings.FORCE_HTTPS_REDIRECT:
            # Check if the request is already HTTPS
            if request.headers.get("x-forwarded-proto", "").lower() != "https":
                # Redirect to HTTPS
                url = request.url.replace(scheme="https")
                return RedirectResponse(url=url, status_code=301)

        # Continue with the request
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive middleware to add security headers to all responses.
    Implements OWASP security headers recommendations for APIs.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Only add security headers if enabled
        if not settings.ENABLE_SECURITY_HEADERS:
            return response

        # Content Security Policy - restrictive for APIs
        if settings.CSP_ENABLED:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "media-src 'none'; "
                "object-src 'none'; "
                "frame-src 'none'; "
                "frame-ancestors 'none'"
            )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=(), "
            "fullscreen=(), "
            "payment=()"
        )

        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Origin-Agent-Cluster for process isolation
        response.headers["Origin-Agent-Cluster"] = "?1"

        # DNS prefetch control
        response.headers["X-DNS-Prefetch-Control"] = "off"

        # Add HSTS header if HTTPS is enabled
        if settings.ENABLE_HTTPS:
            hsts_value = f"max-age={settings.HSTS_MAX_AGE}"
            if settings.HSTS_INCLUDE_SUBDOMAINS:
                hsts_value += "; includeSubDomains"
            if settings.HSTS_PRELOAD:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses with tenant metrics"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json", "/favicon.ico"]
        self.logger = logging.getLogger("chama_wallet.requests")

    async def dispatch(self, request: Request, call_next):
        # Skip logging for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Generate correlation ID for request tracing
        correlation_id = get_request_correlation_id()

        # Start timer
        start_time = time.time()

        # Log request
        self.logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'} - "
            f"User-Agent: {request.headers.get('user-agent', 'unknown')}",
            extra={"correlation_id": correlation_id}
        )

        # Process the request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log request failure
            process_time = time.time() - start_time
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Duration: {process_time:.4f}s",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
            raise

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response
        status_code = response.status_code
        log_level = "WARNING" if status_code >= 400 else "INFO"

        getattr(self.logger, log_level.lower())(
            f"Response: {request.method} {request.url.path} - "
            f"Status: {status_code} - Duration: {process_time:.4f}s",
            extra={"correlation_id": correlation_id}
        )

        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant ID from request URL and set tenant context"""

    def __init__(self, app):
        super().__init__(app)
        # Regex patterns for extracting chama_id from URLs
        self.chama_patterns = [
            re.compile(r'/chamas/(\d+)/?.*'),  # /chamas/{id}/...
            re.compile(r'/api/v\d+/chamas/(\d+)/?.*'),  # Versioned chama routes
        ]

    async def dispatch(self, request: Request, call_next):
        # Extract tenant (chama_id) from URL path
        tenant_id = None
        path = request.url.path

        for pattern in self.chama_patterns:
            match = pattern.match(path)
            if match:
                tenant_id_str = match.group(1)
                try:
                    tenant_id = int(tenant_id_str)
                    break
                except ValueError:
                    # Invalid tenant ID format
                    pass

        if tenant_id is not None:
            # Set tenant context and start metrics tracking for this request
            token = current_tenant.set(tenant_id)
            start_request_metrics(tenant_id)
            success = False
            try:
                response = await call_next(request)
                success = response.status_code < 400
                return response
            finally:
                # End metrics tracking and clean up context
                status_code = 200 if success else 500
                end_request_metrics(request.method, path, status_code)
                current_tenant.reset(token)
        else:
            # No tenant context needed (e.g., user registration, login)
            # Still track global metrics if needed
            start_request_metrics()
            try:
                response = await call_next(request)
                end_request_metrics(request.method, path, response.status_code)
                return response
            except Exception:
                # Ensure metrics are recorded even on failure
                end_request_metrics(request.method, path, 500)
                raise
