import pytest
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from unittest.mock import MagicMock, AsyncMock
from backend.main import chama_wallet_exception_handler, validation_exception_handler, integrity_error_handler, sqlalchemy_exception_handler, http_exception_handler, general_exception_handler


@pytest.mark.asyncio
async def test_chama_wallet_exception_handler():
    """Test ChamaWalletException handler"""
    from backend.exceptions import AuthenticationError

    mock_request = MagicMock(spec=Request)
    exc = AuthenticationError("Invalid credentials")

    handler = chama_wallet_exception_handler(mock_request, exc)

    assert handler.status_code == 401
    assert "Invalid credentials" in handler.detail


@pytest.mark.asyncio
async def test_validation_exception_handler():
    """Test validation error handler"""
    mock_request = MagicMock(spec=Request)
    mock_errors = MagicMock()
    mock_errors.errors.return_value = [{"loc": ["body", "email"], "msg": "invalid email"}]
    exc = RequestValidationError(mock_errors)

    result = validation_exception_handler(mock_request, exc)

    assert result.status_code == 422
    assert "validation_errors" in result.body.decode()


@pytest.mark.asyncio
async def test_integrity_error_handler():
    """Test integrity error handler"""
    mock_request = MagicMock(spec=Request)
    exc = IntegrityError("Duplicate key", None, None)

    result = integrity_error_handler(mock_request, exc)

    assert result.status_code == 400


@pytest.mark.asyncio
async def test_sqlalchemy_exception_handler():
    """Test SQLAlchemy error handler"""
    mock_request = MagicMock(spec=Request)
    exc = SQLAlchemyError("Database error")

    result = sqlalchemy_exception_handler(mock_request, exc)

    assert result.status_code == 500


@pytest.mark.asyncio
async def test_http_exception_handler():
    """Test HTTP exception handler"""
    mock_request = MagicMock(spec=Request)
    exc = HTTPException(status_code=404, detail="Not found")

    result = http_exception_handler(mock_request, exc)

    assert result.status_code == 404
    assert "Not found" in result.detail


@pytest.mark.asyncio
async def test_general_exception_handler():
    """Test general exception handler"""
    mock_request = MagicMock(spec=Request)
    exc = ValueError("Some error")

    result = general_exception_handler(mock_request, exc)

    assert result.status_code == 500
