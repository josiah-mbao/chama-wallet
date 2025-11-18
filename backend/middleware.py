# backend/middleware.py
import time
import logging
import re
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.logging_config import get_request_correlation_id
from backend.database import current_tenant
from backend.metrics import start_request_metrics, end_request_metrics


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


class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log security-related events"""

    def __init__(self, app):
        super().__init__(app)
        self.security_logger = logging.getLogger("chama_wallet.security")

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Log suspicious activities
        suspicious_indicators = []

        # Check for common attack patterns (simplified examples)
        user_agent = request.headers.get("user-agent", "").lower()
        if any(pattern in user_agent for pattern in ["sqlmap", "nmap", "nikto"]):
            suspicious_indicators.append("suspicious_user_agent")

        # Check for excessive request rate (would need rate limiting)
        # This is placeholder - actual implementation would use Redis/caching

        # Log security events
        if suspicious_indicators:
            correlation_id = getattr(logging, 'correlation_id', 'unknown')
            self.security_logger.warning(
                f"Security event detected: {request.method} {request.url.path} - "
                f"Client: {request.client.host if request.client else 'unknown'} - "
                f"Indicators: {', '.join(suspicious_indicators)}",
                extra={"correlation_id": correlation_id}
            )

        return response


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware to log performance metrics for monitoring"""

    def __init__(self, app, slow_request_threshold: float = 2.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.performance_logger = logging.getLogger("chama_wallet.performance")

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log slow requests
        if process_time > self.slow_request_threshold:
            correlation_id = getattr(logging, 'correlation_id', 'unknown')
            self.performance_logger.warning(
                f"Slow request: {request.method} {request.url.path} - "
                f"Duration: {process_time:.4f}s - Status: {response.status_code}",
                extra={"correlation_id": correlation_id}
            )

        # Log high error rates (would need metrics collection)
        # This is placeholder - actual implementation would use Prometheus/statsd

        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to extract tenant ID from request URL and set tenant context"""

    def __init__(self, app):
        super().__init__(app)
        # Regex patterns for extracting chama_id from URLs
        self.chama_patterns = [
            re.compile(r'/chamas/(\d+)/?.*'),  # /chamas/{id}/...
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
            try:
                response = await call_next(request)
                # End metrics tracking with request details
                end_request_metrics(request.method, path, response.status_code)
                return response
            finally:
                # Clean up context
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
