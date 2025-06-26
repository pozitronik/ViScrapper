from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc, asc
from typing import List, Optional
from datetime import datetime, timedelta

from database.session import get_db
from schemas.product import Product, ProductCreate, ProductBase, ProductUpdate
from crud.product import (
    get_product_by_url, create_product, get_product_by_id, 
    update_product, delete_product, get_products
)
from services.image_downloader import download_images
from api.models.responses import (
    SuccessResponse, PaginatedResponse, PaginationInfo, SearchFilters, 
    SortOptions, DeleteResponse, ProductStats
)
from exceptions.base import ProductException, ValidationException
from utils.logger import get_logger
from models.product import Product as ProductModel, Image, Size

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


def apply_filters(query, filters: SearchFilters):
    """Apply search filters to the query."""
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
    
    return query


def apply_sorting(query, sort_by: str, sort_order: str):
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
    has_images: Optional[bool] = Query(None, description="Filter by image presence"),
    has_sizes: Optional[bool] = Query(None, description="Filter by size presence"),
    created_after: Optional[datetime] = Query(None, description="Created after date"),
    created_before: Optional[datetime] = Query(None, description="Created before date"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db)
):
    """
    Get a paginated list of products with optional filtering and sorting.
    
    Supports filtering by:
    - Search query (name, SKU, URL, comment)
    - Price range
    - Currency, availability, color
    - Presence of images/sizes
    - Creation date range
    
    Supports sorting by any product field.
    """
    logger.info(f"Fetching products list - page: {page}, per_page: {per_page}")
    
    # Create search filters
    filters = SearchFilters(
        q=q, min_price=min_price, max_price=max_price,
        currency=currency, availability=availability, color=color,
        has_images=has_images, has_sizes=has_sizes,
        created_after=created_after, created_before=created_before
    )
    
    # Build query
    query = db.query(ProductModel)
    query = apply_filters(query, filters)
    query = apply_sorting(query, sort_by, sort_order)
    
    # Get total count
    total = query.count()
    
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
async def get_product_statistics(db: Session = Depends(get_db)):
    """Get comprehensive product statistics."""
    logger.info("Fetching product statistics")
    
    total_products = db.query(ProductModel).count()
    products_with_images = db.query(ProductModel).filter(ProductModel.images.any()).count()
    products_with_sizes = db.query(ProductModel).filter(ProductModel.sizes.any()).count()
    total_images = db.query(Image).count()
    total_sizes = db.query(Size).count()
    
    # Products added in last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_products_24h = db.query(ProductModel).filter(
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


@router.get("/recent", response_model=SuccessResponse[List[Product]])
async def get_recent_products(
    limit: int = Query(10, ge=1, le=50, description="Number of recent products"),
    db: Session = Depends(get_db)
):
    """Get recently added products."""
    logger.info(f"Fetching {limit} recent products")
    
    products = db.query(ProductModel).order_by(desc(ProductModel.created_at)).limit(limit).all()
    
    logger.info(f"Retrieved {len(products)} recent products")
    
    return SuccessResponse(
        data=products,
        message=f"Retrieved {len(products)} recent products"
    )


@router.get("/search", response_model=PaginatedResponse[Product])
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Search products by name, SKU, URL, or comment."""
    logger.info(f"Searching products with query: '{q}'")
    
    search_term = f"%{q}%"
    query = db.query(ProductModel).filter(
        or_(
            ProductModel.name.ilike(search_term),
            ProductModel.sku.ilike(search_term),
            ProductModel.product_url.ilike(search_term),
            ProductModel.comment.ilike(search_term)
        )
    ).order_by(desc(ProductModel.created_at))
    
    total = query.count()
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()
    
    pagination = calculate_pagination(page, per_page, total)
    
    logger.info(f"Search found {total} products, returning {len(products)} for page {page}")
    
    return PaginatedResponse(
        data=products,
        pagination=pagination,
        message=f"Found {total} products matching search query"
    )


@router.get("/{product_id}", response_model=SuccessResponse[Product])
async def get_product(
    product_id: int = Path(..., ge=1, description="Product ID"),
    db: Session = Depends(get_db)
):
    """Get a specific product by ID."""
    logger.info(f"Fetching product with ID: {product_id}")
    
    product = get_product_by_id(db, product_id=product_id)
    if not product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info(f"Retrieved product: {product.name}")
    
    return SuccessResponse(
        data=product,
        message="Product retrieved successfully"
    )


@router.post("", response_model=SuccessResponse[Product])
async def create_new_product(
    product: ProductCreate,
    download_images_flag: bool = Query(True, description="Whether to download images"),
    db: Session = Depends(get_db)
):
    """
    Create a new product with optional image downloading.
    
    This is an enhanced version of the scrape endpoint that allows
    creating products without mandatory image downloading.
    """
    logger.info(f"Creating new product for URL: {product.product_url}")
    
    # Check if product already exists
    existing_product = get_product_by_url(db, url=str(product.product_url))
    if existing_product:
        logger.warning(f"Product already exists for URL: {product.product_url}")
        raise ProductException(
            message="Product with this URL already exists",
            product_url=str(product.product_url),
            details={"existing_product_id": existing_product.id}
        )
    
    # Download images if requested and URLs provided
    if download_images_flag and product.all_image_urls:
        logger.info(f"Downloading {len(product.all_image_urls)} images")
        image_ids = await download_images(product.all_image_urls)
        product.all_image_urls = image_ids
    
    # Create product
    created_product = create_product(db=db, product=product)
    
    logger.info(f"Successfully created product with ID: {created_product.id}")
    
    return SuccessResponse(
        data=created_product,
        message="Product created successfully"
    )


@router.put("/{product_id}", response_model=SuccessResponse[Product])
async def update_existing_product(
    product_update: ProductUpdate,
    product_id: int = Path(..., ge=1, description="Product ID"),
    db: Session = Depends(get_db)
):
    """Update an existing product."""
    logger.info(f"Updating product with ID: {product_id}")
    
    # Check if product exists
    existing_product = get_product_by_id(db, product_id=product_id)
    if not existing_product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update product
    updated_product = update_product(db=db, product_id=product_id, product_update=product_update)
    
    logger.info(f"Successfully updated product with ID: {product_id}")
    
    return SuccessResponse(
        data=updated_product,
        message="Product updated successfully"
    )


@router.delete("/{product_id}", response_model=DeleteResponse)
async def delete_existing_product(
    product_id: int = Path(..., ge=1, description="Product ID"),
    db: Session = Depends(get_db)
):
    """Delete a product and all its associated data."""
    logger.info(f"Deleting product with ID: {product_id}")
    
    # Check if product exists
    existing_product = get_product_by_id(db, product_id=product_id)
    if not existing_product:
        logger.warning(f"Product not found with ID: {product_id}")
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete product
    success = delete_product(db=db, product_id=product_id)
    if not success:
        logger.error(f"Failed to delete product with ID: {product_id}")
        raise HTTPException(status_code=500, detail="Failed to delete product")
    
    logger.info(f"Successfully deleted product with ID: {product_id}")
    
    return DeleteResponse(
        deleted_id=product_id,
        message="Product deleted successfully"
    )