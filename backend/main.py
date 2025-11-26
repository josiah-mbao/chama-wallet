# backend/main.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.database import get_db
from api.v1 import v1_router
from api.v2 import v2_router
from api import SUPPORTED_VERSIONS, DEFAULT_VERSION, DEPRECATED_VERSIONS
from backend.exceptions import ChamaWalletException
from backend.schemas import ErrorResponse, ValidationErrorResponse, ValidationErrorDetail
from backend.logging_config import setup_logging
from backend.middleware import (
    RequestLoggingMiddleware,
    TenantContextMiddleware
)
from backend.rate_limiting import RateLimitMiddleware
from backend.metrics import get_prometheus_metrics, get_metrics_summary
from starlette_exporter import PrometheusMiddleware, handle_metrics

# Set default SECRET_KEY for local development if not set
if not os.getenv("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "dev_secret_key_local_development_only"

# Configure comprehensive logging
logger = setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    enable_file_logging=os.getenv("ENABLE_FILE_LOGGING", "true").lower() == "true"
)

app = FastAPI(
    title="Chama Wallet API",
)

# Add middleware (order matters - prometheus first, then rate limiting, then request logging, then tenant context)
app.add_middleware(PrometheusMiddleware, app_name="chama-wallet")
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TenantContextMiddleware)

# Include versioned API routes
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])

# Legacy unversioned routes (deprecated - use /api/v1/ instead)
# TODO: Migrate all clients to versioned endpoints and remove
app.include_router(v1_router, prefix="/api", tags=["legacy"])
# Direct billing routes for backward compatibility during testing/migration
app.include_router(v1_router, prefix="", tags=["billing-legacy"])
# Note: WebSocket router temporarily disabled for CI/CD testing
# Will be added to v1 when needed: app.include_router(websockets_router, prefix="/ws", tags=["websockets"])

@app.get("/", tags=["Health"])
def read_root():
    return {
        "message": "Welcome to the Chama Wallet SaaS API",
        "version": "1.0.0",
        "status": "operational",
        "api_versions": SUPPORTED_VERSIONS,
        "default_version": DEFAULT_VERSION,
        "docs": {
            "v1": "/api/v1/docs",
            "v2": "/api/v2/docs"
        }
    }


@app.get("/api-info", tags=["Versioning"])
def get_api_info():
    """Get API versioning information and capabilities."""
    return {
        "title": "Chama Wallet API",
        "version": "1.0.0",
        "supported_versions": SUPPORTED_VERSIONS,
        "deprecated_versions": DEPRECATED_VERSIONS,
        "default_version": DEFAULT_VERSION,
        "versioning_strategy": "URL-based (e.g., /api/v1/endpoint)",
        "documentation": {
            "v1": "/api/v1/docs",
            "v2": "/api/v2/docs"
        },
        "migration_guide": "/api/v1/docs"  # TODO: Create migration guide
    }


@app.get("/metrics", tags=["Metrics"])
def get_metrics():
    """Prometheus metrics endpoint for monitoring"""
    return get_prometheus_metrics()


@app.get("/metrics/summary", tags=["Metrics"])
def get_metrics_summary_endpoint():
    """Human-readable metrics summary for debugging"""
    return get_metrics_summary()


# Global exception handlers
@app.exception_handler(ChamaWalletException)
async def chama_wallet_exception_handler(request: Request, exc: ChamaWalletException):
    """Handle custom ChamaWallet exceptions"""
    logger.warning(f"ChamaWalletException: {exc.detail} (code: {exc.error_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=exc.error_code,
            detail=exc.detail
        ).model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    errors = [
        ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"]
        )
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(errors=errors).model_dump()
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint violations"""
    logger.error(f"Database integrity error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error_code="database_integrity_error",
            detail="Data integrity violation occurred"
        ).model_dump()
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle general SQLAlchemy errors"""
    logger.error(f"Database error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="database_error",
            detail="A database error occurred"
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle standard FastAPI HTTPExceptions"""
    logger.warning(f"HTTPException: {exc.detail} (status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error_code=f"http_{exc.status_code}",
            detail=exc.detail
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error_code="internal_server_error",
            detail="An unexpected error occurred"
        ).model_dump()
    )
