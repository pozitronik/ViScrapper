"""
Utility functions for schema conversion and validation.
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException
from models.product import Product as ProductModel
from api.models.responses import PaginationInfo
from utils.logger import get_logger

logger = get_logger(__name__)


def product_to_dict(product: ProductModel) -> Dict[str, Any]:
    """
    Convert a Product SQLAlchemy model to a dictionary for broadcasting.
    
    Args:
        product: The Product model instance
        
    Returns:
        Dictionary representation of the product
    """
    from schemas.product import Product as ProductSchema
    return ProductSchema.model_validate(product).model_dump()


def calculate_pagination(page: int, per_page: int, total: int) -> PaginationInfo:
    """Calculate pagination information."""
    pages = (total + per_page - 1) // per_page  # Ceiling division
    return PaginationInfo(
        page=page,
        per_page=per_page,
        total=total,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )


def validate_resource_exists(resource: Optional[Any], resource_id: int, 
                           resource_type: str = "Resource") -> None:
    """
    Validate that a resource exists, raising a 404 HTTPException if not.
    
    Args:
        resource: The resource to check (None means not found)
        resource_id: The ID of the resource for logging
        resource_type: The type of resource for error messages
    
    Raises:
        HTTPException: 404 if resource is None
    """
    if not resource:
        logger.warning(f"{resource_type} not found with ID: {resource_id}")
        raise HTTPException(status_code=404, detail=f"{resource_type} not found")