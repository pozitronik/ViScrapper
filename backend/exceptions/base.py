"""
Base exception classes for the VIParser application.
"""

from typing import Any, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class VIParserException(Exception):
    """Base exception class for VIParser application."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception
        
        super().__init__(self.message)
    
    def _log_exception(self):
        """Log the exception with appropriate level and context."""
        log_context = {
            "error_code": self.error_code,
            "details": self.details,
            "exception_type": self.__class__.__name__
        }
        
        if self.original_exception:
            log_context["original_exception"] = str(self.original_exception)
        
        logger.error(f"{self.message} | Context: {log_context}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class ValidationException(VIParserException):
    """Exception raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        # Remove conflicting parameters  
        kwargs.pop('error_code', None)
        
        if field:
            details['field'] = field
        if value is not None:
            details['invalid_value'] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=details,
            **kwargs
        )


class DatabaseException(VIParserException):
    """Exception raised when database operations fail."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        # Remove conflicting parameters
        kwargs.pop('error_code', None)
        
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details=details,
            **kwargs
        )


class ExternalServiceException(VIParserException):
    """Exception raised when external service calls fail."""
    
    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        # Remove conflicting parameters
        kwargs.pop('error_code', None)
        
        if service:
            details['service'] = service
        if url:
            details['url'] = url
        if status_code:
            details['status_code'] = status_code
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
            **kwargs
        )


class ProductException(VIParserException):
    """Exception raised for product-related operations."""
    
    def __init__(
        self,
        message: str,
        product_url: Optional[str] = None,
        product_id: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        # Remove conflicting parameters
        kwargs.pop('error_code', None)
        
        if product_url:
            details['product_url'] = product_url
        if product_id:
            details['product_id'] = product_id
        
        super().__init__(
            message=message,
            error_code="PRODUCT_ERROR",
            details=details,
            **kwargs
        )


class ImageDownloadException(ExternalServiceException):
    """Exception raised when image download fails."""
    
    def __init__(
        self,
        message: str,
        image_url: Optional[str] = None,
        **kwargs
    ):
        # Extract details and remove conflicting parameters
        details = kwargs.pop('details', {})
        kwargs.pop('error_code', None)  # Remove to avoid conflict
        
        if image_url:
            details['image_url'] = image_url
        
        super().__init__(
            message=message,
            service="image_downloader",
            url=image_url,
            details=details,
            **kwargs
        )
        # Override the error_code after parent initialization
        self.error_code = "IMAGE_DOWNLOAD_ERROR"