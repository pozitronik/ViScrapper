from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List, Optional, Any, Dict
from datetime import datetime, timezone

T = TypeVar('T')


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: T
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginationInfo(BaseModel):
    """Pagination information."""
    page: int = Field(ge=1, description="Current page number")
    per_page: int = Field(ge=1, le=100, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    success: bool = True
    message: str = "Data retrieved successfully"
    data: List[T]
    pagination: PaginationInfo
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthStatus(BaseModel):
    """Health check response."""
    status: str = Field(description="System status")
    version: str = Field(description="API version")
    uptime: float = Field(description="System uptime in seconds")
    database: str = Field(description="Database connection status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductStats(BaseModel):
    """Product statistics."""
    total_products: int = Field(ge=0, description="Total number of products")
    products_with_images: int = Field(ge=0, description="Products that have images")
    products_with_sizes: int = Field(ge=0, description="Products that have sizes")
    total_images: int = Field(ge=0, description="Total number of images")
    total_sizes: int = Field(ge=0, description="Total number of sizes")
    recent_products_24h: int = Field(ge=0, description="Products added in last 24 hours")
    average_images_per_product: float = Field(ge=0, description="Average images per product")


class SearchFilters(BaseModel):
    """Search and filter parameters."""
    q: Optional[str] = Field(None, description="Search query for name, SKU, or URL")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    currency: Optional[str] = Field(None, description="Currency filter")
    availability: Optional[str] = Field(None, description="Availability filter")
    color: Optional[str] = Field(None, description="Color filter")
    has_images: Optional[bool] = Field(None, description="Filter products with/without images")
    has_sizes: Optional[bool] = Field(None, description="Filter products with/without sizes")
    created_after: Optional[datetime] = Field(None, description="Created after date filter")
    created_before: Optional[datetime] = Field(None, description="Created before date filter")


class SortOptions(BaseModel):
    """Sorting options."""
    sort_by: str = Field("created_at", description="Field to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class DeleteResponse(BaseModel):
    """Response for delete operations."""
    success: bool = True
    message: str = "Resource deleted successfully"
    deleted_id: int = Field(description="ID of the deleted resource")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FileDeleteResponse(BaseModel):
    """Response for file delete operations."""
    success: bool = True
    message: str = "File deleted successfully"
    deleted_filename: str = Field(description="Name of the deleted file")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BulkOperationResponse(BaseModel):
    """Response for bulk operations."""
    success: bool = True
    message: str = "Bulk operation completed"
    processed: int = Field(ge=0, description="Number of items processed")
    succeeded: int = Field(ge=0, description="Number of items that succeeded")
    failed: int = Field(ge=0, description="Number of items that failed")
    errors: Optional[List[str]] = Field(None, description="List of error messages for failed items")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))