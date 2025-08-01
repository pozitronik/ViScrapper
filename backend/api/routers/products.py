from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, desc, asc, and_
from sqlalchemy.sql import ColumnElement
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta, timezone

from database.session import get_db
from schemas.product import Product, ProductCreate, ProductUpdate
from crud.product import (
    create_product, get_product_by_id,
    update_product
)
from crud.delete_operations import (
    delete_product_with_mode, restore_product, get_deleted_products,
    permanently_delete_old_soft_deleted
)
from enums.delete_mode import DeleteMode
from services.image_downloader import download_images
from api.models.responses import (
    SuccessResponse, PaginatedResponse, PaginationInfo, SearchFilters,
    DeleteResponse, ProductStats
)
from exceptions.base import ProductException
from utils.logger import get_logger
from models.product import Product as ProductModel, Image, Size
from services.websocket_service import websocket_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


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


def apply_filters(query: Any, filters: SearchFilters, include_deleted: bool = False) -> Any:
    """Apply search filters to the query."""
    # Always exclude soft-deleted records unless explicitly requested
    if not include_deleted:
        query = query.filter(ProductModel.deleted_at.is_(None))

    if filters.q:
        search_term = f"%{filters.q}%"
        query = query.filter(
            or_(
                ProductModel.name.ilike(search_term),
                ProductModel.sku.ilike(search_term),
                ProductModel.product_url.ilike(search_term),
                ProductModel.comment.ilike(search_term)
            )
        )

    if filters.min_price is not None:
        query = query.filter(ProductModel.price >= filters.min_price)

    if filters.max_price is not None:
        query = query.filter(ProductModel.price <= filters.max_price)

    if filters.currency:
        query = query.filter(ProductModel.currency.ilike(f"%{filters.currency}%"))

    if filters.availability:
        query = query.filter(ProductModel.availability.ilike(f"%{filters.availability}%"))

    if filters.color:
        query = query.filter(ProductModel.color.ilike(f"%{filters.color}%"))

    if filters.store:
        query = query.filter(ProductModel.store.ilike(f"%{filters.store}%"))

    if filters.has_images is not None:
        if filters.has_images:
            query = query.filter(ProductModel.images.any())
        else:
            query = query.filter(~ProductModel.images.any())

    if filters.has_sizes is not None:
        if filters.has_sizes:
            query = query.filter(ProductModel.sizes.any())
        else:
            query = query.filter(~ProductModel.sizes.any())

    if filters.created_after:
        query = query.filter(ProductModel.created_at >= filters.created_after)

    if filters.created_before:
        query = query.filter(ProductModel.created_at <= filters.created_before)

    if filters.telegram_posted is not None:
        if filters.telegram_posted:
            query = query.filter(ProductModel.telegram_posted_at.isnot(None))
        else:
            query = query.filter(ProductModel.telegram_posted_at.is_(None))

    return query


def apply_sorting(query: Any, sort_by: str, sort_order: str) -> Any:
    """Apply sorting to the query."""
    if not hasattr(ProductModel, sort_by):
        sort_by = "created_at"  # Default fallback

    column = getattr(ProductModel, sort_by)
    if sort_order == "asc":
        return query.order_by(asc(column))
    else:
        return query.order_by(desc(column))


@router.get("", response_model=PaginatedResponse[Product])
async def list_products(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        q: Optional[str] = Query(None, description="Search query"),
        min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
        max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
        currency: Optional[str] = Query(None, description="Currency filter"),
        availability: Optional[str] = Query(None, description="Availability filter"),
        color: Optional[str] = Query(None, description="Color filter"),
        store: Optional[str] = Query(None, description="Store filter"),
        has_images: Optional[bool] = Query(None, description="Filter by image presence"),
        has_sizes: Optional[bool] = Query(None, description="Filter by size presence"),
        telegram_posted: Optional[bool] = Query(None, description="Filter by telegram posting status"),
        created_after: Optional[datetime] = Query(None, description="Created after date"),
        created_before: Optional[datetime] = Query(None, description="Created before date"),
        include_deleted: Optional[bool] = Query(False, description="Include soft-deleted products"),
        only_deleted: Optional[bool] = Query(False, description="Show only soft-deleted products"),
        sort_by: str = Query("created_at", description="Field to sort by"),
        sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
        db: Session = Depends(get_db)
) -> PaginatedResponse[Product]:
    """
    Get a paginated list of products with optional filtering and sorting.
    
    Supports filtering by:
    - Search query (name, SKU, URL, comment)
    - Price range
    - Currency, availability, color, store
    - Presence of images/sizes
    - Telegram posting status
    - Creation date range
    
    Supports sorting by any product field.
    """
    logger.info(f"Fetching products list - page: {page}, per_page: {per_page}")

    # Create search filters
    filters = SearchFilters(
        q=q, min_price=min_price, max_price=max_price,
        currency=currency, availability=availability, color=color,
        store=store, has_images=has_images, has_sizes=has_sizes, telegram_posted=telegram_posted,
        created_after=created_after, created_before=created_before
    )

    # Build query with eager loading to prevent N+1 queries
    query = db.query(ProductModel).options(
        joinedload(ProductModel.images),
        joinedload(ProductModel.sizes)
    )
    # Determine include_deleted logic based on parameters
    actual_include_deleted = bool(include_deleted or only_deleted)
    query = apply_filters(query, filters, include_deleted=actual_include_deleted)
    
    # If only_deleted is True, filter to show only deleted products
    if only_deleted:
        query = query.filter(ProductModel.deleted_at.isnot(None))
    query = apply_sorting(query, sort_by, sort_order)

    # Get total count using optimized query (without joins)
    count_query = db.query(ProductModel.id)
    count_query = apply_filters(count_query, filters, include_deleted=actual_include_deleted)
    if only_deleted:
        count_query = count_query.filter(ProductModel.deleted_at.isnot(None))
    total = count_query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()

    # Calculate pagination info
    pagination = calculate_pagination(page, per_page, total)

    logger.info(f"Retrieved {len(products)} products (page {page}/{pagination.pages})")

    return PaginatedResponse(
        data=products,
        pagination=pagination,
        message=f"Retrieved {len(products)} products"
    )


@router.get("/stats", response_model=SuccessResponse[ProductStats])
async def get_product_statistics(db: Session = Depends(get_db)) -> SuccessResponse[ProductStats]:
    """Get comprehensive product statistics."""
    logger.info("Fetching product statistics")

    # Use optimized count queries selecting only IDs
    total_products = db.query(ProductModel.id).filter(ProductModel.deleted_at.is_(None)).count()
    
    # Use EXISTS for more efficient counting of products with relationships
    products_with_images = db.query(ProductModel.id).filter(
        ProductModel.deleted_at.is_(None),
        db.query(Image.id).filter(Image.product_id == ProductModel.id, Image.deleted_at.is_(None)).exists()
    ).count()
    
    products_with_sizes = db.query(ProductModel.id).filter(
        ProductModel.deleted_at.is_(None),
        db.query(Size.id).filter(Size.product_id == ProductModel.id, Size.deleted_at.is_(None)).exists()
    ).count()
    
    total_images = db.query(Image.id).filter(Image.deleted_at.is_(None)).count()
    total_sizes = db.query(Size.id).filter(Size.deleted_at.is_(None)).count()

    # Products added in last 24 hours
    twenty_four_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_products_24h = db.query(ProductModel.id).filter(
        ProductModel.deleted_at.is_(None),
        ProductModel.created_at >= twenty_four_hours_ago
    ).count()

    # Average images per product
    avg_images = 0.0
    if total_products > 0:
        avg_images = total_images / total_products

    stats = ProductStats(
        total_products=total_products,
        products_with_images=products_with_images,
        products_with_sizes=products_with_sizes,
        total_images=total_images,
        total_sizes=total_sizes,
        recent_products_24h=recent_products_24h,
        average_images_per_product=round(avg_images, 2)
    )

    logger.info(f"Product statistics: {total_products} total products")

    return SuccessResponse(
        data=stats,
        message="Product statistics retrieved successfully"
    )


@router.get("/deleted", response_model=PaginatedResponse[Product])
async def list_deleted_products(
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
) -> PaginatedResponse[Product]:
    """Get a paginated list of soft-deleted products."""
    logger.info(f"Fetching deleted products list - page: {page}, per_page: {per_page}")

    # Calculate offset
    offset = (page - 1) * per_page

    # Get deleted products
    products = get_deleted_products(db, skip=offset, limit=per_page)

    # Get total count of deleted products
    total = db.query(ProductModel).filter(ProductModel.deleted_at.isnot(None)).count()

    # Calculate pagination info
    pagination = calculate_pagination(page, per_page, total)

    logger.info(f"Retrieved {len(products)} deleted products (page {page}/{pagination.pages})")

    # Convert SQLAlchemy models to Pydantic schemas
    product_schemas = [Product.model_validate(product) for product in products]

    return PaginatedResponse(
        data=product_schemas,
        pagination=pagination,
        message=f"Retrieved {len(products)} deleted products"
    )


@router.get("/recent", response_model=SuccessResponse[List[Product]])
async def get_recent_products(
        limit: int = Query(10, ge=1, le=50, description="Number of recent products"),
        db: Session = Depends(get_db)
) -> SuccessResponse[List[Product]]:
    """Get recently added products."""
    logger.info(f"Fetching {limit} recent products")

    products = db.query(ProductModel).options(
        joinedload(ProductModel.images),
        joinedload(ProductModel.sizes)
    ).filter(
        ProductModel.deleted_at.is_(None)
    ).order_by(desc(ProductModel.created_at)).limit(limit).all()

    logger.info(f"Retrieved {len(products)} recent products")

    # Convert SQLAlchemy models to Pydantic schemas
    product_schemas = [Product.model_validate(product) for product in products]

    return SuccessResponse(
        data=product_schemas,
        message=f"Retrieved {len(products)} recent products"
    )


@router.post("/cleanup-old-deleted", response_model=SuccessResponse[Dict[str, Any]])
async def cleanup_old_deleted_products(
        days_old: int = Query(30, ge=0, le=365, description="Days old threshold for permanent deletion"),
        db: Session = Depends(get_db)
) -> SuccessResponse[Dict[str, Any]]:
    """Permanently delete products that have been soft-deleted for more than specified days."""
    logger.info(f"Cleaning up products soft-deleted more than {days_old} days ago")

    # Permanently delete old soft-deleted products
    deleted_count = permanently_delete_old_soft_deleted(db=db, days_old=days_old)

    logger.info(f"Permanently deleted {deleted_count} old soft-deleted products")

    return SuccessResponse(
        data={"deleted_count": deleted_count, "days_threshold": days_old},
        message=f"Permanently deleted {deleted_count} products that were soft-deleted more than {days_old} days ago"
    )


@router.get("/search", response_model=PaginatedResponse[Product])
async def search_products(
        q: Optional[str] = Query(None, min_length=1, description="General search query (for backward compatibility)"),
        sku: Optional[str] = Query(None, min_length=1, description="Search by SKU"),
        name: Optional[str] = Query(None, min_length=1, description="Search by product name"),
        url: Optional[str] = Query(None, min_length=1, description="Search by product URL"),
        comment: Optional[str] = Query(None, min_length=1, description="Search by comment"),
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
        db: Session = Depends(get_db)
) -> PaginatedResponse[Product]:
    """
    Search products by specific fields or general query.
    
    You can search by specific fields (sku, name, url, comment) or use the general 'q' parameter.
    If both specific fields and 'q' are provided, specific fields take precedence.
    """
    # Validate that at least one search parameter is provided
    if not any([q, sku, name, url, comment]):
        raise HTTPException(
            status_code=400, 
            detail="At least one search parameter must be provided (q, sku, name, url, or comment)"
        )
    
    # Build search conditions
    search_conditions: List[ColumnElement[bool]] = []
    search_info = []
    
    if sku:
        logger.info(f"Searching products by SKU: '{sku}'")
        search_conditions.append(ProductModel.sku.ilike(f"%{sku}%"))
        search_info.append(f"SKU: '{sku}'")
    
    if name:
        logger.info(f"Searching products by name: '{name}'")
        search_conditions.append(ProductModel.name.ilike(f"%{name}%"))
        search_info.append(f"name: '{name}'")
    
    if url:
        logger.info(f"Searching products by URL: '{url}'")
        search_conditions.append(ProductModel.product_url.ilike(f"%{url}%"))
        search_info.append(f"URL: '{url}'")
    
    if comment:
        logger.info(f"Searching products by comment: '{comment}'")
        search_conditions.append(ProductModel.comment.ilike(f"%{comment}%"))
        search_info.append(f"comment: '{comment}'")
    
    # If no specific fields provided, use general query (backward compatibility)
    if not search_conditions and q:
        logger.info(f"Searching products with general query: '{q}'")
        search_term = f"%{q}%"
        search_conditions.append(
            or_(
                ProductModel.name.ilike(search_term),
                ProductModel.sku.ilike(search_term),
                ProductModel.product_url.ilike(search_term),
                ProductModel.comment.ilike(search_term)
            )
        )
        search_info.append(f"general query: '{q}'")

    # Build final query
    query = db.query(ProductModel).options(
        joinedload(ProductModel.images),
        joinedload(ProductModel.sizes)
    ).filter(
        ProductModel.deleted_at.is_(None),
        and_(*search_conditions) if len(search_conditions) > 1 else search_conditions[0]
    ).order_by(desc(ProductModel.created_at))

    total = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()

    pagination = calculate_pagination(page, per_page, total)

    search_criteria = ", ".join(search_info)
    logger.info(f"Search by {search_criteria} found {total} products, returning {len(products)} for page {page}")

    # Convert SQLAlchemy models to Pydantic schemas
    product_schemas = [Product.model_validate(product) for product in products]

    return PaginatedResponse(
        data=product_schemas,
        pagination=pagination,
        message=f"Found {total} products matching search criteria: {search_criteria}"
    )


@router.get("/{product_id}", response_model=SuccessResponse[Product])
async def get_product(
        product_id: int = Path(..., ge=1, description="Product ID"),
        db: Session = Depends(get_db)
) -> SuccessResponse[Product]:
    """Get a specific product by ID."""
    logger.info(f"Fetching product with ID: {product_id}")

    product = get_product_by_id(db, product_id=product_id)
    if not product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")

    logger.info(f"Retrieved product: {product.name}")

    return SuccessResponse(
        data=Product.model_validate(product),
        message="Product retrieved successfully"
    )


@router.post("", response_model=SuccessResponse[Product])
async def create_new_product(
        product: ProductCreate,
        download_images_flag: bool = Query(True, description="Whether to download images"),
        db: Session = Depends(get_db)
) -> SuccessResponse[Product]:
    """
    Create a new product with optional image downloading.
    
    This is an enhanced version of the scrape endpoint that allows
    creating products without mandatory image downloading.
    """
    logger.info(f"Creating new product for URL: {product.product_url}")

    # Check if product already exists by SKU (primary identifier)
    from crud.product import get_product_by_sku
    existing_product = get_product_by_sku(db, sku=product.sku)
    if existing_product:
        logger.warning(f"Product already exists for SKU: {product.sku}")
        raise ProductException(
            message="Product with this SKU already exists",
            product_url=str(product.product_url) if product.product_url else None,
            details={"existing_product_id": existing_product.id, "sku": product.sku}
        )

    # Download images if requested and URLs provided
    if download_images_flag and product.all_image_urls:
        logger.info(f"Downloading {len(product.all_image_urls)} images")
        image_metadata = await download_images(product.all_image_urls)
        product.all_image_urls = [img['image_id'] if isinstance(img, dict) else img for img in image_metadata]

    # Create product
    created_product = create_product(db=db, product=product)

    # Broadcast the new product to all connected WebSocket clients
    from utils.schema_utils import product_to_dict
    product_dict = product_to_dict(created_product)
    await websocket_manager.broadcast_product_created(product_dict)

    logger.info(f"Successfully created product with ID: {created_product.id}")

    return SuccessResponse(
        data=Product.model_validate(created_product),
        message="Product created successfully"
    )


@router.put("/{product_id}", response_model=SuccessResponse[Product])
async def update_existing_product(
        product_update: ProductUpdate,
        product_id: int = Path(..., ge=1, description="Product ID"),
        db: Session = Depends(get_db)
) -> SuccessResponse[Product]:
    """Update an existing product."""
    logger.info(f"Updating product with ID: {product_id}")

    # Check if product exists
    existing_product = get_product_by_id(db, product_id=product_id)
    if not existing_product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")

    # Update product
    updated_product = update_product(db=db, product_id=product_id, product_update=product_update)

    # Broadcast the updated product to all connected WebSocket clients
    from utils.schema_utils import product_to_dict
    product_dict = product_to_dict(updated_product)
    await websocket_manager.broadcast_product_updated(product_dict)

    logger.info(f"Successfully updated product with ID: {product_id}")

    return SuccessResponse(
        data=Product.model_validate(updated_product),
        message="Product updated successfully"
    )


@router.delete("/{product_id}", response_model=DeleteResponse)
async def delete_existing_product(
        product_id: int = Path(..., ge=1, description="Product ID"),
        delete_mode: DeleteMode = Query(DeleteMode.SOFT, description="Delete mode: soft (default) or hard"),
        db: Session = Depends(get_db)
) -> DeleteResponse:
    """Delete a product and all its associated data with configurable delete mode."""
    logger.info(f"Deleting product with ID: {product_id} using {delete_mode} delete")

    # Check if product exists (include soft-deleted for hard delete)
    include_deleted = (delete_mode == DeleteMode.HARD)
    existing_product = get_product_by_id(db, product_id=product_id, include_deleted=include_deleted)
    if not existing_product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")

    # Delete product with specified mode
    success = delete_product_with_mode(db=db, product_id=product_id, delete_mode=delete_mode)
    if not success:
        logger.error(f"Failed to {delete_mode} delete product with ID: {product_id}")
        raise HTTPException(status_code=500, detail=f"Failed to {delete_mode} delete product")

    # Broadcast the product deletion to all connected WebSocket clients
    await websocket_manager.broadcast_product_deleted(product_id)

    delete_message = f"Product {delete_mode} deleted successfully"
    logger.info(f"Successfully {delete_mode} deleted product with ID: {product_id}")

    return DeleteResponse(
        deleted_id=product_id,
        message=delete_message
    )


@router.post("/{product_id}/restore", response_model=SuccessResponse[Product])
async def restore_deleted_product(
        product_id: int = Path(..., ge=1, description="Product ID"),
        db: Session = Depends(get_db)
) -> SuccessResponse[Product]:
    """Restore a soft-deleted product."""
    logger.info(f"Restoring soft-deleted product with ID: {product_id}")

    # Check if product exists and is soft-deleted
    existing_product = get_product_by_id(db, product_id=product_id, include_deleted=True)
    if not existing_product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")

    if existing_product.deleted_at is None:
        logger.warning(f"Product {product_id} is not soft-deleted")
        raise HTTPException(status_code=400, detail="Product is not deleted and cannot be restored")

    # Restore product
    success = restore_product(db=db, product_id=product_id)
    if not success:
        logger.error(f"Failed to restore product with ID: {product_id}")
        raise HTTPException(status_code=500, detail="Failed to restore product")

    # Get restored product
    restored_product = get_product_by_id(db, product_id=product_id)
    if not restored_product:
        logger.error(f"Product not found after restore with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found after restore")

    # Broadcast the product restoration to all connected WebSocket clients
    from utils.schema_utils import product_to_dict
    product_dict = product_to_dict(restored_product)
    await websocket_manager.broadcast_product_created(product_dict)  # Reuse created event

    logger.info(f"Successfully restored product with ID: {product_id}")

    return SuccessResponse(
        data=Product.model_validate(restored_product),
        message="Product restored successfully"
    )


@router.delete("/{product_id}/images/{image_id}")
async def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db)
) -> SuccessResponse[Dict[str, Any]]:
    """Delete a specific image from a product."""
    from crud.product import get_product_by_id
    from crud.product import delete_product_image as crud_delete_image
    
    # Verify product exists
    product = get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete the image
    deleted_image = crud_delete_image(db, product_id, image_id)
    if not deleted_image:
        raise HTTPException(status_code=404, detail="Image not found for this product")
    
    return SuccessResponse(
        data={"deleted_image_id": image_id, "deleted_image_url": deleted_image.url},
        message="Image deleted successfully"
    )
