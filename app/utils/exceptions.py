"""
Custom Exception Classes

Fungsi file ini:
- Define custom exceptions untuk berbagai error cases
- Consistent error handling across the application
- Better error messages untuk frontend
"""

from fastapi import HTTPException, status


class SmartWealthException(HTTPException):
    """Base exception untuk SmartWealth"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = None,
        details: dict | None = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.details = details


class NotFoundError(SmartWealthException):
    """Resource not found (404)"""
    
    def __init__(self, resource: str, identifier: str = None):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} with id '{identifier}' not found"
        
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_code="NOT_FOUND"
        )


class AlreadyExistsError(SmartWealthException):
    """Resource already exists (409)"""
    
    def __init__(self, resource: str, field: str = None, value: str = None):
        detail = f"{resource} already exists"
        if field and value:
            detail = f"{resource} with {field} '{value}' already exists"
        
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="ALREADY_EXISTS"
        )


class ForbiddenError(SmartWealthException):
    """Access forbidden (403)"""
    
    def __init__(self, detail: str = "You don't have permission to access this resource"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="FORBIDDEN"
        )


class ValidationError(SmartWealthException):
    """Validation error (400)"""
    
    def __init__(self, detail: str, field: str = None):
        if field:
            detail = f"Validation error on field '{field}': {detail}"
        
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="VALIDATION_ERROR"
        )


class InsufficientBalanceError(SmartWealthException):
    """Insufficient balance for transaction (400)"""
    
    def __init__(self, asset_name: str, available: str, required: str):
        detail = (
            f"Insufficient balance for {asset_name}. "
            f"Available: {available}, Required: {required}"
        )
        
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="INSUFFICIENT_BALANCE"
        )


class InvalidTransactionError(SmartWealthException):
    """Invalid transaction (400)"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="INVALID_TRANSACTION"
        )


class ExternalAPIError(SmartWealthException):
    """External API error (502)"""
    
    def __init__(self, service: str, detail: str = None):
        error_detail = f"Failed to fetch data from {service}"
        if detail:
            error_detail = f"{error_detail}: {detail}"
        
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=error_detail,
            error_code="EXTERNAL_API_ERROR"
        )


class RateLimitError(SmartWealthException):
    """Rate limit exceeded (429)"""
    
    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED"
        )
