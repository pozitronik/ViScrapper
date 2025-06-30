"""
Error handlers for FastAPI application.
"""

import traceback
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic_core import ValidationError

from exceptions.base import (
    VIParserException,
    ValidationException,
    DatabaseException,
    ExternalServiceException,
    ProductException,
    ImageDownloadException
)
from utils.logger import get_logger

logger = get_logger(__name__)


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_type: Type of error
        message: Error message
        details: Additional error details
        error_code: Application-specific error code
        
    Returns:
        JSONResponse with standardized error format
    """
    content = {
        "error": {
            "type": error_type,
            "message": message,
            "code": error_code,
            "details": details or {}
        }
    }
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


async def viparser_exception_handler(request: Request, exc: VIParserException) -> JSONResponse:
    """Handle custom VIParser exceptions."""
    logger.error(f"VIParser exception on {request.url}: {exc.message}")
    
    # Map exception types to HTTP status codes
    status_code_map = {
        ValidationException: 400,
        ProductException: 409,  # Conflict for duplicate products
        DatabaseException: 500,
        ExternalServiceException: 502,  # Bad Gateway for external service issues
        ImageDownloadException: 502,
    }
    
    status_code = status_code_map.get(type(exc), 500)
    
    return create_error_response(
        status_code=status_code,
        error_type=exc.__class__.__name__,
        message=exc.message,
        details=exc.details,
        error_code=exc.error_code
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    logger.warning(f"HTTP exception on {request.url}: {exc.status_code} - {exc.detail}")
    
    return create_error_response(
        status_code=exc.status_code,
        error_type="HTTPException",
        message=exc.detail,
        error_code=f"HTTP_{exc.status_code}"
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI request validation errors."""
    logger.warning(f"Request validation error on {request.url}: {exc}")
    
    # Extract validation error details
    details = {
        'validation_errors': exc.errors()
    }
    
    return create_error_response(
        status_code=422,
        error_type="ValidationError",
        message="Input validation failed",
        details=details,
        error_code="VALIDATION_ERROR"
    )


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    logger.warning(f"Validation error on {request.url}: {exc}")
    
    # Extract validation error details
    details = {}
    if hasattr(exc, 'errors'):
        details['validation_errors'] = exc.errors()
    
    return create_error_response(
        status_code=422,
        error_type="ValidationError",
        message="Input validation failed",
        details=details,
        error_code="VALIDATION_ERROR"
    )


async def database_exception_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Handle SQLAlchemy integrity errors."""
    logger.error(f"Database integrity error on {request.url}: {exc}")
    
    # Extract constraint information
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    
    # Determine specific constraint violation
    if "UNIQUE constraint failed" in error_msg:
        message = "Duplicate data detected"
        error_code = "DUPLICATE_ENTRY"
    elif "NOT NULL constraint failed" in error_msg:
        message = "Required field is missing"
        error_code = "MISSING_REQUIRED_FIELD"
    elif "FOREIGN KEY constraint failed" in error_msg:
        message = "Invalid reference to related data"
        error_code = "INVALID_REFERENCE"
    else:
        message = "Database constraint violation"
        error_code = "CONSTRAINT_VIOLATION"
    
    return create_error_response(
        status_code=409,  # Conflict
        error_type="DatabaseIntegrityError",
        message=message,
        details={"database_error": error_msg},
        error_code=error_code
    )


async def operational_exception_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """Handle SQLAlchemy operational errors."""
    logger.error(f"Database operational error on {request.url}: {exc}")
    
    return create_error_response(
        status_code=503,  # Service Unavailable
        error_type="DatabaseOperationalError",
        message="Database service temporarily unavailable",
        details={"database_error": str(exc.orig) if hasattr(exc, 'orig') else str(exc)},
        error_code="DATABASE_UNAVAILABLE"
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all other unhandled exceptions."""
    # Log the full traceback for debugging
    logger.error(f"Unhandled exception on {request.url}: {exc}\n{traceback.format_exc()}")
    
    return create_error_response(
        status_code=500,
        error_type="InternalServerError",
        message="An internal server error occurred",
        error_code="INTERNAL_ERROR"
    )


def setup_error_handlers(app):
    """
    Set up all error handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Custom exception handlers (order matters - more specific first)
    app.add_exception_handler(VIParserException, viparser_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(IntegrityError, database_exception_handler)
    app.add_exception_handler(OperationalError, operational_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Error handlers configured successfully")