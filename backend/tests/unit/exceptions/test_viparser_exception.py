"""
Comprehensive unit tests for VIParser custom exception classes.

This module contains extensive tests for all exception classes in the VIParser
application, covering initialization, logging, serialization, inheritance,
and edge cases.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

from exceptions.base import (
    VIParserException,
    ValidationException,
    DatabaseException,
    ExternalServiceException,
    ProductException,
    ImageDownloadException
)


class TestVIParserException:
    """Test suite for the base VIParserException class."""

    def test_basic_initialization(self):
        """Test basic exception initialization with message only."""
        exc = VIParserException("Test error message")
        
        assert str(exc) == "Test error message"
        assert exc.message == "Test error message"
        assert exc.error_code is None
        assert exc.details == {}
        assert exc.original_exception is None

    def test_full_initialization(self):
        """Test exception initialization with all parameters."""
        original_exc = ValueError("Original error")
        details = {"key": "value", "count": 42}
        
        exc = VIParserException(
            message="Custom error",
            error_code="CUSTOM_ERROR",
            details=details,
            original_exception=original_exc
        )
        
        assert exc.message == "Custom error"
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == details
        assert exc.original_exception is original_exc

    def test_details_default_to_empty_dict(self):
        """Test that details parameter defaults to empty dict when None."""
        exc = VIParserException("Test", details=None)
        assert exc.details == {}

    def test_inheritance_from_exception(self):
        """Test that VIParserException inherits from Exception."""
        exc = VIParserException("Test")
        assert isinstance(exc, Exception)

    def test_to_dict_method(self):
        """Test the to_dict method for API response serialization."""
        exc = VIParserException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"field": "value"}
        )
        
        result = exc.to_dict()
        expected = {
            "error": "VIParserException",
            "message": "Test error",
            "error_code": "TEST_ERROR",
            "details": {"field": "value"}
        }
        
        assert result == expected

    def test_to_dict_with_none_values(self):
        """Test to_dict method with None values."""
        exc = VIParserException("Test error")
        
        result = exc.to_dict()
        expected = {
            "error": "VIParserException",
            "message": "Test error",
            "error_code": None,
            "details": {}
        }
        
        assert result == expected

    @patch('exceptions.base.logger')
    def test_log_exception_basic(self, mock_logger):
        """Test the _log_exception method with basic parameters."""
        exc = VIParserException("Test error", error_code="TEST_ERROR")
        exc._log_exception()
        
        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        
        # Check the logged message contains our error
        call_args = mock_logger.error.call_args[0][0]
        assert "Test error" in call_args

    @patch('exceptions.base.logger')
    def test_log_exception_with_original_exception(self, mock_logger):
        """Test logging with original exception included."""
        original_exc = ValueError("Original error")
        exc = VIParserException(
            "Wrapper error",
            original_exception=original_exc
        )
        
        exc._log_exception()
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "Wrapper error" in call_args
        assert "Original error" in call_args

    @patch('exceptions.base.logger')
    def test_log_exception_with_details(self, mock_logger):
        """Test logging with details included."""
        details = {"user_id": 123, "action": "delete"}
        exc = VIParserException(
            "Operation failed",
            details=details
        )
        
        exc._log_exception()
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args[0][0]
        assert "Operation failed" in call_args

    def test_exception_message_propagation(self):
        """Test that exception message is properly set for Python's Exception base."""
        exc = VIParserException("Test message")
        
        # Test string representation
        assert str(exc) == "Test message"
        
        # Test args property (from Exception base class)
        assert exc.args == ("Test message",)

    def test_exception_equality(self):
        """Test exception equality and hashing."""
        exc1 = VIParserException("Same message", error_code="SAME")
        exc2 = VIParserException("Same message", error_code="SAME")
        exc3 = VIParserException("Different message", error_code="SAME")
        
        # Exceptions are objects, so they should not be equal even with same values
        assert exc1 is not exc2
        assert exc1 is not exc3

    def test_exception_repr(self):
        """Test string representation of exception."""
        exc = VIParserException("Test message")
        repr_str = repr(exc)
        
        assert "VIParserException" in repr_str
        assert "Test message" in repr_str


class TestValidationException:
    """Test suite for ValidationException class."""

    def test_basic_initialization(self):
        """Test basic ValidationException initialization."""
        exc = ValidationException("Validation failed")
        
        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == {}

    def test_initialization_with_field(self):
        """Test ValidationException with field parameter."""
        exc = ValidationException("Invalid email", field="email")
        
        assert exc.message == "Invalid email"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"

    def test_initialization_with_value(self):
        """Test ValidationException with value parameter."""
        exc = ValidationException("Invalid value", value=123)
        
        assert exc.message == "Invalid value"
        assert exc.details["invalid_value"] == "123"  # Should be stringified

    def test_initialization_with_field_and_value(self):
        """Test ValidationException with both field and value."""
        exc = ValidationException(
            "Invalid age",
            field="age",
            value=-5
        )
        
        assert exc.details["field"] == "age"
        assert exc.details["invalid_value"] == "-5"

    def test_none_value_handling(self):
        """Test that None values are not included in details."""
        exc = ValidationException("Error", value=None)
        
        # value=None should not add invalid_value to details
        assert "invalid_value" not in exc.details

    def test_additional_details(self):
        """Test ValidationException with additional details."""
        custom_details = {"custom_key": "custom_value"}
        exc = ValidationException(
            "Validation error",
            field="username",
            details=custom_details
        )
        
        assert exc.details["field"] == "username"
        assert exc.details["custom_key"] == "custom_value"

    def test_error_code_override_ignored(self):
        """Test that error_code parameter is ignored (filtered out)."""
        exc = ValidationException(
            "Error",
            error_code="CUSTOM_ERROR"  # Should be ignored
        )
        
        assert exc.error_code == "VALIDATION_ERROR"

    def test_inheritance_from_viparser_exception(self):
        """Test that ValidationException inherits from VIParserException."""
        exc = ValidationException("Test")
        assert isinstance(exc, VIParserException)
        assert isinstance(exc, Exception)

    def test_to_dict_method(self):
        """Test ValidationException to_dict method."""
        exc = ValidationException("Invalid data", field="email")
        
        result = exc.to_dict()
        
        assert result["error"] == "ValidationException"
        assert result["message"] == "Invalid data"
        assert result["error_code"] == "VALIDATION_ERROR"
        assert result["details"]["field"] == "email"


class TestDatabaseException:
    """Test suite for DatabaseException class."""

    def test_basic_initialization(self):
        """Test basic DatabaseException initialization."""
        exc = DatabaseException("Database error")
        
        assert exc.message == "Database error"
        assert exc.error_code == "DATABASE_ERROR"
        assert exc.details == {}

    def test_initialization_with_operation(self):
        """Test DatabaseException with operation parameter."""
        exc = DatabaseException("Query failed", operation="SELECT")
        
        assert exc.details["operation"] == "SELECT"

    def test_initialization_with_table(self):
        """Test DatabaseException with table parameter."""
        exc = DatabaseException("Table error", table="products")
        
        assert exc.details["table"] == "products"

    def test_initialization_with_operation_and_table(self):
        """Test DatabaseException with both operation and table."""
        exc = DatabaseException(
            "Insert failed",
            operation="INSERT",
            table="users"
        )
        
        assert exc.details["operation"] == "INSERT"
        assert exc.details["table"] == "users"

    def test_additional_details(self):
        """Test DatabaseException with additional details."""
        original_exc = ConnectionError("Connection lost")
        exc = DatabaseException(
            "Database unavailable",
            operation="UPDATE",
            original_exception=original_exc
        )
        
        assert exc.details["operation"] == "UPDATE"
        assert exc.original_exception is original_exc

    def test_error_code_override_ignored(self):
        """Test that error_code parameter is ignored."""
        exc = DatabaseException(
            "Error",
            error_code="CUSTOM_ERROR"
        )
        
        assert exc.error_code == "DATABASE_ERROR"


class TestExternalServiceException:
    """Test suite for ExternalServiceException class."""

    def test_basic_initialization(self):
        """Test basic ExternalServiceException initialization."""
        exc = ExternalServiceException("Service error")
        
        assert exc.message == "Service error"
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"
        assert exc.details == {}

    def test_initialization_with_service(self):
        """Test ExternalServiceException with service parameter."""
        exc = ExternalServiceException("API error", service="payment_api")
        
        assert exc.details["service"] == "payment_api"

    def test_initialization_with_url(self):
        """Test ExternalServiceException with URL parameter."""
        exc = ExternalServiceException(
            "HTTP error", 
            url="https://api.example.com/users"
        )
        
        assert exc.details["url"] == "https://api.example.com/users"

    def test_initialization_with_status_code(self):
        """Test ExternalServiceException with status_code parameter."""
        exc = ExternalServiceException("API error", status_code=404)
        
        assert exc.details["status_code"] == 404

    def test_initialization_with_all_parameters(self):
        """Test ExternalServiceException with all parameters."""
        exc = ExternalServiceException(
            "Service unavailable",
            service="user_service",
            url="https://api.example.com/users/123",
            status_code=503
        )
        
        assert exc.details["service"] == "user_service"
        assert exc.details["url"] == "https://api.example.com/users/123"
        assert exc.details["status_code"] == 503


class TestProductException:
    """Test suite for ProductException class."""

    def test_basic_initialization(self):
        """Test basic ProductException initialization."""
        exc = ProductException("Product error")
        
        assert exc.message == "Product error"
        assert exc.error_code == "PRODUCT_ERROR"
        assert exc.details == {}

    def test_initialization_with_product_url(self):
        """Test ProductException with product_url parameter."""
        exc = ProductException(
            "Product not found",
            product_url="https://example.com/product/123"
        )
        
        assert exc.details["product_url"] == "https://example.com/product/123"

    def test_initialization_with_product_id(self):
        """Test ProductException with product_id parameter."""
        exc = ProductException("Product error", product_id=456)
        
        assert exc.details["product_id"] == 456

    def test_initialization_with_both_identifiers(self):
        """Test ProductException with both product_url and product_id."""
        exc = ProductException(
            "Product conflict",
            product_url="https://example.com/product/789",
            product_id=789
        )
        
        assert exc.details["product_url"] == "https://example.com/product/789"
        assert exc.details["product_id"] == 789


class TestImageDownloadException:
    """Test suite for ImageDownloadException class."""

    def test_basic_initialization(self):
        """Test basic ImageDownloadException initialization."""
        exc = ImageDownloadException("Image download failed")
        
        assert exc.message == "Image download failed"
        assert exc.error_code == "IMAGE_DOWNLOAD_ERROR"
        # Should inherit service from parent
        assert exc.details.get("service") == "image_downloader"

    def test_initialization_with_image_url(self):
        """Test ImageDownloadException with image_url parameter."""
        image_url = "https://example.com/image.jpg"
        exc = ImageDownloadException(
            "Download failed",
            image_url=image_url
        )
        
        assert exc.details["image_url"] == image_url
        # Should also set URL in parent class
        assert exc.details.get("url") == image_url

    def test_inheritance_from_external_service_exception(self):
        """Test that ImageDownloadException inherits from ExternalServiceException."""
        exc = ImageDownloadException("Download error")
        
        assert isinstance(exc, ExternalServiceException)
        assert isinstance(exc, VIParserException)
        assert isinstance(exc, Exception)

    def test_service_field_automatic_population(self):
        """Test that service field is automatically set."""
        exc = ImageDownloadException("Error")
        
        assert exc.details.get("service") == "image_downloader"

    def test_error_code_override(self):
        """Test that error_code is correctly overridden."""
        exc = ImageDownloadException("Error")
        
        # Should be IMAGE_DOWNLOAD_ERROR, not EXTERNAL_SERVICE_ERROR
        assert exc.error_code == "IMAGE_DOWNLOAD_ERROR"

    def test_with_status_code_from_parent(self):
        """Test ImageDownloadException with status_code from parent class."""
        exc = ImageDownloadException(
            "HTTP error",
            image_url="https://example.com/image.jpg",
            status_code=404
        )
        
        assert exc.details["status_code"] == 404
        assert exc.details["image_url"] == "https://example.com/image.jpg"
        assert exc.details["url"] == "https://example.com/image.jpg"


class TestExceptionInteractions:
    """Test interactions between different exception types."""

    def test_exception_chaining(self):
        """Test exception chaining with original_exception."""
        original = ValueError("Original error")
        wrapper = VIParserException(
            "Wrapped error",
            original_exception=original
        )
        
        assert wrapper.original_exception is original
        assert str(wrapper) == "Wrapped error"
        assert str(wrapper.original_exception) == "Original error"

    def test_exception_context_preservation(self):
        """Test that exception context is preserved through inheritance."""
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            wrapper = ProductException(
                "Product processing failed",
                product_id=123,
                original_exception=e
            )
            
            assert wrapper.original_exception is e
            assert wrapper.details["product_id"] == 123

    @patch('exceptions.base.logger')
    def test_logging_across_exception_types(self, mock_logger):
        """Test that all exception types can be logged."""
        exceptions = [
            VIParserException("Base error"),
            ValidationException("Validation error", field="email"),
            DatabaseException("DB error", table="users"),
            ExternalServiceException("API error", service="payment"),
            ProductException("Product error", product_id=123),
            ImageDownloadException("Download error", image_url="http://example.com/img.jpg")
        ]
        
        for exc in exceptions:
            mock_logger.reset_mock()
            exc._log_exception()
            mock_logger.error.assert_called_once()

    def test_serialization_consistency(self):
        """Test that all exception types can be serialized to dict consistently."""
        exceptions = [
            VIParserException("Base error", error_code="BASE"),
            ValidationException("Validation error", field="email"),
            DatabaseException("DB error", table="users"),
            ExternalServiceException("API error", service="payment"),
            ProductException("Product error", product_id=123),
            ImageDownloadException("Download error", image_url="http://example.com/img.jpg")
        ]
        
        for exc in exceptions:
            result = exc.to_dict()
            
            # All should have these keys
            assert "error" in result
            assert "message" in result
            assert "error_code" in result
            assert "details" in result
            
            # Error should be the class name
            assert result["error"] == exc.__class__.__name__
            
            # Message should match
            assert result["message"] == exc.message

    def test_exception_details_immutability(self):
        """Test that exception details don't interfere with each other."""
        exc1 = ValidationException("Error 1", field="field1")
        exc2 = ValidationException("Error 2", field="field2")
        
        assert exc1.details["field"] == "field1"
        assert exc2.details["field"] == "field2"
        
        # Modifying one shouldn't affect the other
        exc1.details["new_key"] = "new_value"
        assert "new_key" not in exc2.details


class TestExceptionEdgeCases:
    """Test edge cases and error conditions for exception classes."""

    def test_empty_message(self):
        """Test exception with empty message."""
        exc = VIParserException("")
        assert exc.message == ""
        assert str(exc) == ""

    def test_none_message_handling(self):
        """Test exception with None as message."""
        exc = VIParserException(None)
        assert exc.message is None
        assert str(exc) == "None"

    def test_very_long_message(self):
        """Test exception with very long message."""
        long_message = "x" * 10000
        exc = VIParserException(long_message)
        assert exc.message == long_message

    def test_unicode_message(self):
        """Test exception with unicode characters."""
        unicode_message = "Error: 测试错误 🚫"
        exc = VIParserException(unicode_message)
        assert exc.message == unicode_message

    def test_details_with_complex_objects(self):
        """Test exception details with complex object values."""
        complex_details = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "tuple": (1, 2, 3),
            "none": None
        }
        
        exc = VIParserException("Error", details=complex_details)
        assert exc.details == complex_details

    def test_details_modification_after_creation(self):
        """Test modifying details after exception creation."""
        exc = VIParserException("Error", details={"initial": "value"})
        
        # Should be able to modify details
        exc.details["new_key"] = "new_value"
        assert exc.details["new_key"] == "new_value"
        assert exc.details["initial"] == "value"

    def test_original_exception_with_different_types(self):
        """Test original_exception with various exception types."""
        base_exceptions = [
            ValueError("Value error"),
            TypeError("Type error"),
            KeyError("Key error"),
            AttributeError("Attribute error"),
            RuntimeError("Runtime error")
        ]
        
        for original in base_exceptions:
            wrapper = VIParserException(
                "Wrapper error",
                original_exception=original
            )
            assert wrapper.original_exception is original
            assert isinstance(wrapper.original_exception, type(original))