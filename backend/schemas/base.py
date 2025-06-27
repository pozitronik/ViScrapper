"""
Base schemas for API responses
"""
from pydantic import BaseModel
from typing import TypeVar, Generic, Optional

T = TypeVar('T')


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper"""
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None
    error: Optional[str] = None


class PaginationInfo(BaseModel):
    """Pagination information"""
    total: int
    skip: int
    limit: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response"""
    success: bool
    data: list[T]
    pagination: PaginationInfo
    message: Optional[str] = None