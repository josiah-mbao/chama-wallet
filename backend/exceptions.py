# backend/exceptions.py

from fastapi import HTTPException


class ChamaWalletException(HTTPException):
    """Base exception for Chama Wallet API errors"""

    def __init__(self, status_code: int, detail: str, error_code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code if error_code is not None \
            else f"api_{status_code}"


# Authentication & Authorization Errors
class AuthenticationError(ChamaWalletException):
    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="auth_invalid_credentials"
        )


class AuthorizationError(ChamaWalletException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=403,
            detail=detail,
            error_code="auth_insufficient_permissions"
        )


class InactiveUserError(ChamaWalletException):
    def __init__(self, detail: str = "Inactive user"):
        super().__init__(
            status_code=401,
            detail=detail,
            error_code="auth_inactive_user"
        )


# Resource Errors
class ResourceNotFoundError(ChamaWalletException):
    def __init__(self, resource_type: str, resource_id: str = None):
        detail = f"{resource_type} not found"
        if resource_id is not None:
            detail += f" with id {resource_id}"
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="resource_not_found"
        )


class DuplicateResourceError(ChamaWalletException):
    def __init__(self, resource_type: str, detail: str = "Resource already exists"):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="resource_duplicate"
        )


# Business Logic Errors
class AlreadyMemberError(DuplicateResourceError):
    def __init__(self, detail: str = "User is already a member of this chama"):
        super().__init__("MembershipView", detail)


class InvalidOperationError(ChamaWalletException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="operation_invalid"
        )


class ValidationError(ChamaWalletException):
    def __init__(self, detail: str):
        super().__init__(
            status_code=422,
            detail=detail,
            error_code="validation_error"
        )
