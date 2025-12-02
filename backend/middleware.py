"""
Middleware for HTTPS enforcement and security headers.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from starlette.requests import Request
from backend.config import settings


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
