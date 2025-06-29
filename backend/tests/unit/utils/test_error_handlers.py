"""
Comprehensive unit tests for error handler utilities.

This module contains extensive tests for FastAPI error handling functions including
create_error_response, viparser_exception_handler, http_exception_handler,
request_validation_exception_handler, database_exception_handler, and setup_error_handlers.
"""

import pytest
import traceback
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
from utils.error_handlers import (
    create_error_response,
    viparser_exception_handler,
    http_exception_handler,
    request_validation_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    operational_exception_handler,
    general_exception_handler,
    setup_error_handlers
)


class TestCreateErrorResponse:
    """Test suite for create_error_response function."""

    def test_create_error_response_basic(self):
        """Test basic error response creation."""
        response = create_error_response(
            status_code=400,
            error_type="ValidationError",
            message="Invalid input"
        )
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        # Check response content
        content = response.body.decode()
        assert "ValidationError" in content
        assert "Invalid input" in content

    def test_create_error_response_with_details(self):
        """Test error response creation with details."""
        details = {"field": "email", "issue": "invalid format"}
        
        response = create_error_response(
            status_code=422,
            error_type="ValidationError",
            message="Validation failed",
            details=details,
            error_code="VALIDATION_FAILED"
        )
        
        assert response.status_code == 422
        
        # Parse JSON content
        import json
        content = json.loads(response.body.decode())
        
        assert content["error"]["type"] == "ValidationError"
        assert content["error"]["message"] == "Validation failed"
        assert content["error"]["code"] == "VALIDATION_FAILED"
        assert content["error"]["details"] == details

    def test_create_error_response_with_none_details(self):
        """Test error response creation with None details."""
        response = create_error_response(
            status_code=500,
            error_type="InternalError",
            message="Something went wrong",
            details=None
        )
        
        import json
        content = json.loads(response.body.decode())
        
        assert content["error"]["details"] == {}

    def test_create_error_response_with_none_error_code(self):
        """Test error response creation with None error code."""
        response = create_error_response(
            status_code=404,
            error_type="NotFound",
            message="Resource not found",
            error_code=None
        )
        
        import json
        content = json.loads(response.body.decode())
        
        assert content["error"]["code"] is None

    def test_create_error_response_structure(self):
        """Test that error response has correct structure."""
        response = create_error_response(
            status_code=403,
            error_type="AccessDenied",
            message="Permission denied"
        )
        
        import json
        content = json.loads(response.body.decode())
        
        # Verify required structure
        assert "error" in content
        assert "type" in content["error"]
        assert "message" in content["error"]
        assert "code" in content["error"]
        assert "details" in content["error"]


class TestVIParserExceptionHandler:
    """Test suite for viparser_exception_handler function."""

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_validation_exception(self):
        """Test handler for ValidationException."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/test"
        
        exception = ValidationException("Invalid data", details={"field": "name"})
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await viparser_exception_handler(mock_request, exception)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 400
        
        # Check logging
        mock_logger.error.assert_called_once()
        
        # Check response content
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "ValidationException"
        assert content["error"]["message"] == "Invalid data"

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_product_exception(self):
        """Test handler for ProductException."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/products"
        
        exception = ProductException("Product already exists")
        
        response = await viparser_exception_handler(mock_request, exception)
        
        assert response.status_code == 409  # Conflict
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "ProductException"
        assert content["error"]["code"] == "PRODUCT_ERROR"

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_database_exception(self):
        """Test handler for DatabaseException."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = DatabaseException("Connection lost")
        
        response = await viparser_exception_handler(mock_request, exception)
        
        assert response.status_code == 500
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "DatabaseException"

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_external_service_exception(self):
        """Test handler for ExternalServiceException."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = ExternalServiceException("API unavailable")
        
        response = await viparser_exception_handler(mock_request, exception)
        
        assert response.status_code == 502  # Bad Gateway

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_image_download_exception(self):
        """Test handler for ImageDownloadException."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/images"
        
        exception = ImageDownloadException("Download failed")
        
        response = await viparser_exception_handler(mock_request, exception)
        
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_viparser_exception_handler_unknown_exception_type(self):
        """Test handler for unknown VIParserException subclass."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        # Create a custom VIParserException subclass
        class CustomException(VIParserException):
            pass
        
        exception = CustomException("Unknown error")
        
        response = await viparser_exception_handler(mock_request, exception)
        
        # Should default to 500
        assert response.status_code == 500


class TestHTTPExceptionHandler:
    """Test suite for http_exception_handler function."""

    @pytest.mark.asyncio
    async def test_http_exception_handler_404(self):
        """Test handler for 404 HTTP exception."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/notfound"
        
        exception = HTTPException(status_code=404, detail="Not found")
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await http_exception_handler(mock_request, exception)
        
        assert response.status_code == 404
        
        # Check logging
        mock_logger.warning.assert_called_once()
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "HTTPException"
        assert content["error"]["message"] == "Not found"
        assert content["error"]["code"] == "HTTP_404"

    @pytest.mark.asyncio
    async def test_http_exception_handler_403(self):
        """Test handler for 403 HTTP exception."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/forbidden"
        
        exception = HTTPException(status_code=403, detail="Access denied")
        
        response = await http_exception_handler(mock_request, exception)
        
        assert response.status_code == 403
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "HTTP_403"

    @pytest.mark.asyncio
    async def test_http_exception_handler_500(self):
        """Test handler for 500 HTTP exception."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/error"
        
        exception = HTTPException(status_code=500, detail="Internal server error")
        
        response = await http_exception_handler(mock_request, exception)
        
        assert response.status_code == 500
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["code"] == "HTTP_500"


class TestRequestValidationExceptionHandler:
    """Test suite for request_validation_exception_handler function."""

    @pytest.mark.asyncio
    async def test_request_validation_exception_handler(self):
        """Test handler for RequestValidationError."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        # Create mock validation errors
        validation_errors = [
            {"loc": ["body", "email"], "msg": "field required", "type": "value_error.missing"},
            {"loc": ["body", "age"], "msg": "must be positive", "type": "value_error"}
        ]
        
        exception = Mock(spec=RequestValidationError)
        exception.errors.return_value = validation_errors
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await request_validation_exception_handler(mock_request, exception)
        
        assert response.status_code == 422
        
        # Check logging
        mock_logger.warning.assert_called_once()
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "ValidationError"
        assert content["error"]["message"] == "Input validation failed"
        assert content["error"]["code"] == "VALIDATION_ERROR"
        assert content["error"]["details"]["validation_errors"] == validation_errors


class TestValidationExceptionHandler:
    """Test suite for validation_exception_handler function."""

    @pytest.mark.asyncio
    async def test_validation_exception_handler_with_errors(self):
        """Test handler for ValidationError with errors method."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        validation_errors = [
            {"loc": ["name"], "msg": "String too short", "type": "value_error"}
        ]
        
        exception = Mock(spec=ValidationError)
        exception.errors.return_value = validation_errors
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await validation_exception_handler(mock_request, exception)
        
        assert response.status_code == 422
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["details"]["validation_errors"] == validation_errors

    @pytest.mark.asyncio
    async def test_validation_exception_handler_without_errors(self):
        """Test handler for ValidationError without errors method."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=ValidationError)
        # Remove errors attribute
        del exception.errors
        
        response = await validation_exception_handler(mock_request, exception)
        
        assert response.status_code == 422
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["details"] == {}


class TestDatabaseExceptionHandler:
    """Test suite for database_exception_handler function."""

    @pytest.mark.asyncio
    async def test_database_exception_handler_unique_constraint(self):
        """Test handler for UNIQUE constraint violation."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        # Create mock IntegrityError with UNIQUE constraint
        exception = Mock(spec=IntegrityError)
        exception.orig = Mock()
        exception.orig.__str__ = Mock(return_value="UNIQUE constraint failed: products.sku")
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await database_exception_handler(mock_request, exception)
        
        assert response.status_code == 409
        
        mock_logger.error.assert_called_once()
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "DatabaseIntegrityError"
        assert content["error"]["message"] == "Duplicate data detected"
        assert content["error"]["code"] == "DUPLICATE_ENTRY"

    @pytest.mark.asyncio
    async def test_database_exception_handler_not_null_constraint(self):
        """Test handler for NOT NULL constraint violation."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=IntegrityError)
        exception.orig = Mock()
        exception.orig.__str__ = Mock(return_value="NOT NULL constraint failed: products.name")
        
        response = await database_exception_handler(mock_request, exception)
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["message"] == "Required field is missing"
        assert content["error"]["code"] == "MISSING_REQUIRED_FIELD"

    @pytest.mark.asyncio
    async def test_database_exception_handler_foreign_key_constraint(self):
        """Test handler for FOREIGN KEY constraint violation."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=IntegrityError)
        exception.orig = Mock()
        exception.orig.__str__ = Mock(return_value="FOREIGN KEY constraint failed")
        
        response = await database_exception_handler(mock_request, exception)
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["message"] == "Invalid reference to related data"
        assert content["error"]["code"] == "INVALID_REFERENCE"

    @pytest.mark.asyncio
    async def test_database_exception_handler_other_constraint(self):
        """Test handler for other constraint violations."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=IntegrityError)
        exception.orig = Mock()
        exception.orig.__str__ = Mock(return_value="CHECK constraint failed")
        
        response = await database_exception_handler(mock_request, exception)
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["message"] == "Database constraint violation"
        assert content["error"]["code"] == "CONSTRAINT_VIOLATION"

    @pytest.mark.asyncio
    async def test_database_exception_handler_no_orig(self):
        """Test handler for IntegrityError without orig attribute."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=IntegrityError)
        # Remove orig attribute
        del exception.orig
        exception.__str__ = Mock(return_value="Database integrity error")
        
        response = await database_exception_handler(mock_request, exception)
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["details"]["database_error"] == "Database integrity error"


class TestOperationalExceptionHandler:
    """Test suite for operational_exception_handler function."""

    @pytest.mark.asyncio
    async def test_operational_exception_handler_with_orig(self):
        """Test handler for OperationalError with orig attribute."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=OperationalError)
        exception.orig = Mock()
        exception.orig.__str__ = Mock(return_value="database is locked")
        
        with patch('utils.error_handlers.logger') as mock_logger:
            response = await operational_exception_handler(mock_request, exception)
        
        assert response.status_code == 503
        
        mock_logger.error.assert_called_once()
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "DatabaseOperationalError"
        assert content["error"]["message"] == "Database service temporarily unavailable"
        assert content["error"]["code"] == "DATABASE_UNAVAILABLE"
        assert content["error"]["details"]["database_error"] == "database is locked"

    @pytest.mark.asyncio
    async def test_operational_exception_handler_without_orig(self):
        """Test handler for OperationalError without orig attribute."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Mock(spec=OperationalError)
        # Remove orig attribute
        del exception.orig
        exception.__str__ = Mock(return_value="Connection failed")
        
        response = await operational_exception_handler(mock_request, exception)
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["details"]["database_error"] == "Connection failed"


class TestGeneralExceptionHandler:
    """Test suite for general_exception_handler function."""

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test handler for general exceptions."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        exception = Exception("Unexpected error")
        
        with patch('utils.error_handlers.logger') as mock_logger:
            with patch('utils.error_handlers.traceback') as mock_traceback:
                mock_traceback.format_exc.return_value = "Traceback info..."
                
                response = await general_exception_handler(mock_request, exception)
        
        assert response.status_code == 500
        
        # Check logging with traceback
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args[0][0]
        assert "Unexpected error" in log_call
        assert "Traceback info..." in log_call
        
        import json
        content = json.loads(response.body.decode())
        assert content["error"]["type"] == "InternalServerError"
        assert content["error"]["message"] == "An internal server error occurred"
        assert content["error"]["code"] == "INTERNAL_ERROR"

    @pytest.mark.asyncio
    async def test_general_exception_handler_various_exceptions(self):
        """Test handler with various exception types."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/api"
        
        test_exceptions = [
            KeyError("missing key"),
            ValueError("invalid value"),
            TypeError("wrong type"),
            AttributeError("missing attribute"),
            ImportError("module not found")
        ]
        
        for exception in test_exceptions:
            with patch('utils.error_handlers.logger'):
                response = await general_exception_handler(mock_request, exception)
                
                assert response.status_code == 500
                
                import json
                content = json.loads(response.body.decode())
                assert content["error"]["type"] == "InternalServerError"


class TestSetupErrorHandlers:
    """Test suite for setup_error_handlers function."""

    def test_setup_error_handlers(self):
        """Test that all error handlers are registered."""
        mock_app = Mock()
        
        with patch('utils.error_handlers.logger') as mock_logger:
            setup_error_handlers(mock_app)
        
        # Verify all exception handlers were added
        expected_calls = [
            (VIParserException, viparser_exception_handler),
            (HTTPException, http_exception_handler),
            (RequestValidationError, request_validation_exception_handler),
            (ValidationError, validation_exception_handler),
            (IntegrityError, database_exception_handler),
            (OperationalError, operational_exception_handler),
            (Exception, general_exception_handler)
        ]
        
        assert mock_app.add_exception_handler.call_count == len(expected_calls)
        
        # Check that correct handlers were registered
        for i, (exc_type, handler) in enumerate(expected_calls):
            call_args = mock_app.add_exception_handler.call_args_list[i]
            assert call_args[0][0] == exc_type
            assert call_args[0][1] == handler
        
        # Check success logging
        mock_logger.info.assert_called_once_with("Error handlers configured successfully")

    def test_setup_error_handlers_order_matters(self):
        """Test that error handlers are registered in correct order."""
        mock_app = Mock()
        
        setup_error_handlers(mock_app)
        
        # Get the registered exception types in order
        registered_types = [
            call[0][0] for call in mock_app.add_exception_handler.call_args_list
        ]
        
        # VIParserException should come before Exception (more specific first)
        viparser_index = registered_types.index(VIParserException)
        general_index = registered_types.index(Exception)
        assert viparser_index < general_index
        
        # HTTPException should come before Exception
        http_index = registered_types.index(HTTPException)
        assert http_index < general_index
        
        # IntegrityError should come before Exception
        integrity_index = registered_types.index(IntegrityError)
        assert integrity_index < general_index


class TestErrorHandlerIntegration:
    """Integration tests for error handlers."""

    @pytest.mark.asyncio
    async def test_error_response_consistency(self):
        """Test that all error handlers produce consistent response format."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/test"
        
        # Test different exception handlers
        test_cases = [
            (ValidationException("test"), viparser_exception_handler),
            (HTTPException(status_code=404, detail="not found"), http_exception_handler),
            (Exception("general error"), general_exception_handler)
        ]
        
        for exception, handler in test_cases:
            with patch('utils.error_handlers.logger'):
                response = await handler(mock_request, exception)
                
                assert isinstance(response, JSONResponse)
                
                import json
                content = json.loads(response.body.decode())
                
                # All responses should have consistent structure
                assert "error" in content
                assert "type" in content["error"]
                assert "message" in content["error"]
                assert "code" in content["error"]
                assert "details" in content["error"]

    @pytest.mark.asyncio
    async def test_error_handler_logging_consistency(self):
        """Test that error handlers log consistently."""
        mock_request = Mock(spec=Request)
        mock_request.url = "http://example.com/test"
        
        with patch('utils.error_handlers.logger') as mock_logger:
            # Test ValidationException
            exception = ValidationException("validation failed")
            await viparser_exception_handler(mock_request, exception)
            
            # Should log at ERROR level
            mock_logger.error.assert_called()
            
            mock_logger.reset_mock()
            
            # Test HTTPException
            exception = HTTPException(status_code=404, detail="not found")
            await http_exception_handler(mock_request, exception)
            
            # Should log at WARNING level for HTTP exceptions
            mock_logger.warning.assert_called()

    def test_error_handler_setup_integration(self):
        """Test complete error handler setup integration."""
        mock_app = Mock()
        
        # Setup all handlers
        setup_error_handlers(mock_app)
        
        # Verify app was properly configured
        assert mock_app.add_exception_handler.call_count == 7
        
        # Verify all major exception types are covered
        registered_types = [
            call[0][0] for call in mock_app.add_exception_handler.call_args_list
        ]
        
        expected_types = [
            VIParserException,
            HTTPException,
            RequestValidationError,
            ValidationError,
            IntegrityError,
            OperationalError,
            Exception
        ]
        
        for expected_type in expected_types:
            assert expected_type in registered_types