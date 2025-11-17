# backend/main.py
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from backend.database import get_db
from backend.routers.users import router as users_router
from backend.routers.chamas import router as chamas_router
from backend.routers.members import router as members_router
from backend.exceptions import ChamaWalletException
from backend.schemas import ErrorResponse, ValidationErrorResponse, ValidationErrorDetail
from backend.logging_config import setup_logging
from backend.middleware import RequestLoggingMiddleware
from backend.rate_limiting import RateLimitMiddleware

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

# Add middleware (order matters - rate limiting should be first)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Include all routers
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(chamas_router, prefix="/chamas", tags=["chamas"])
app.include_router(members_router, prefix="/chamas/{chama_id}", tags=["members"])

@app.get("/", tags=["Health"])
def read_root():
    return {"message": "Welcome to the Chama Wallet API - Status: Operational"}


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
