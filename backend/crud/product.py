from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Optional
from models.product import Product, Image, Size
from schemas.product import ProductCreate, ProductBase, ProductUpdate
from utils.logger import get_logger
from utils.database import atomic_transaction, validate_product_constraints, bulk_create_relationships
from exceptions.base import DatabaseException, ValidationException, ProductException

logger = get_logger(__name__)


def get_product_by_url(db: Session, url: str, include_deleted: bool = False):
    """
    Get a product by its URL.
    
    Args:
        db: Database session
        url: Product URL to search for
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with URL: {url}")
    query = db.query(Product).filter(Product.product_url == url)
    
    if not include_deleted:
        query = query.filter(Product.deleted_at.is_(None))
    
    product = query.first()
    if product:
        logger.debug(f"Found product with ID: {product.id}")
    else:
        logger.debug(f"No product found for URL: {url}")
    return product


def create_product(db: Session, product: ProductCreate):
    """
    Create a new product with images and sizes in a single atomic transaction.
    
    Args:
        db: Database session
        product: Product data to create
        
    Returns:
        Created product with relationships loaded
        
    Raises:
        ValidationException: If product data validation fails
        DatabaseException: If database operation fails
        ProductException: If product creation logic fails
    """
    logger.info(f"Creating product: {product.name} ({product.product_url})")
    
    try:
        # Validate input data before attempting database operations
        product_dict = product.model_dump()
        validate_product_constraints(product_dict)
        
    except ValueError as e:
        raise ValidationException(
            message=str(e),
            details={"product_url": str(product.product_url)},
            original_exception=e
        )
    
    try:
        # Use atomic transaction for consistency
        with atomic_transaction(db):
            # Create the main product record
            db_product = Product(
                product_url=str(product.product_url),
                name=product.name,
                sku=product.sku,
                price=product.price,
                currency=product.currency,
                availability=product.availability,
                color=product.color,
                composition=product.composition,
                item=product.item,
                comment=product.comment,
            )

            db.add(db_product)
            # Flush to get the ID without committing the transaction
            db.flush()
            logger.debug(f"Created product with ID: {db_product.id}")

            # Add images using bulk creation for better performance
            if product.all_image_urls:
                logger.info(f"Adding {len(product.all_image_urls)} images to product ID: {db_product.id}")
                bulk_create_relationships(db, db_product.id, product.all_image_urls, Image, 'url')

            # Add sizes using bulk creation for better performance
            if product.available_sizes:
                logger.info(f"Adding {len(product.available_sizes)} sizes to product ID: {db_product.id}")
                bulk_create_relationships(db, db_product.id, product.available_sizes, Size, 'name')

            # Transaction will be committed by the context manager
            logger.debug("All product data prepared for atomic commit")

    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # Determine specific constraint violation
        if "UNIQUE constraint failed: products.product_url" in error_msg:
            raise ProductException(
                message="Product with this URL already exists",
                product_url=str(product.product_url),
                details={"constraint": "product_url_unique"},
                original_exception=e
            )
        elif "UNIQUE constraint failed: products.sku" in error_msg:
            raise ProductException(
                message="Product with this SKU already exists",
                product_url=str(product.product_url),
                details={"constraint": "sku_unique", "sku": product.sku},
                original_exception=e
            )
        elif "UNIQUE constraint failed: images.url" in error_msg:
            raise DatabaseException(
                message="Duplicate image URL detected",
                operation="create_product",
                table="images",
                details={"product_url": str(product.product_url)},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during product creation",
                operation="create_product",
                table="products",
                details={"product_url": str(product.product_url), "error": error_msg},
                original_exception=e
            )
    
    except OperationalError as e:
        raise DatabaseException(
            message="Database operational error during product creation",
            operation="create_product",
            details={"product_url": str(product.product_url)},
            original_exception=e
        )
    
    except Exception as e:
        raise ProductException(
            message="Unexpected error during product creation",
            product_url=str(product.product_url),
            details={"error_type": type(e).__name__},
            original_exception=e
        )

    try:
        # After successful commit, load the complete product with relationships
        db_product = db.query(Product).options(
            joinedload(Product.images), 
            joinedload(Product.sizes)
        ).filter(Product.id == db_product.id).first()
        
        if not db_product:
            raise ProductException(
                message="Product was created but could not be retrieved",
                details={"product_url": str(product.product_url)}
            )

        logger.info(f"Successfully created product ID: {db_product.id} with {len(db_product.images)} images and {len(db_product.sizes)} sizes")
        return db_product
        
    except Exception as e:
        raise DatabaseException(
            message="Failed to retrieve created product",
            operation="get_product",
            table="products",
            details={"product_url": str(product.product_url)},
            original_exception=e
        )


def get_product_by_id(db: Session, product_id: int, include_deleted: bool = False) -> Optional[Product]:
    """
    Get a product by its ID with all relationships loaded.
    
    Args:
        db: Database session
        product_id: Product ID to search for
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with ID: {product_id}")
    
    try:
        query = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.sizes)
        ).filter(Product.id == product_id)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        product = query.first()
        
        if product:
            logger.debug(f"Found product: {product.name}")
        else:
            logger.debug(f"No product found for ID: {product_id}")
        
        return product
        
    except Exception as e:
        logger.error(f"Error retrieving product by ID {product_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve product by ID",
            operation="get_product_by_id",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def get_products(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    load_relationships: bool = True,
    include_deleted: bool = False
) -> List[Product]:
    """
    Get a list of products with pagination.
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        load_relationships: Whether to load images and sizes
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        List of products
    """
    logger.debug(f"Fetching products with skip={skip}, limit={limit}")
    
    try:
        query = db.query(Product)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        if load_relationships:
            query = query.options(
                joinedload(Product.images),
                joinedload(Product.sizes)
            )
        
        products = query.offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(products)} products")
        
        return products
        
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        raise DatabaseException(
            message="Failed to retrieve products list",
            operation="get_products",
            table="products",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Product:
    """
    Update an existing product.
    
    Args:
        db: Database session
        product_id: ID of the product to update
        product_update: Product data to update
        
    Returns:
        Updated product instance
        
    Raises:
        ProductException: If product not found or update fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Updating product with ID: {product_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing product
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ProductException(
                    message="Product not found for update",
                    details={"product_id": product_id}
                )
            
            # Update fields that are provided (not None)
            update_data = product_update.model_dump(exclude_unset=True, exclude_none=True)
            
            # Validate the update data
            if update_data:
                # Convert URL to string if present
                if 'product_url' in update_data:
                    update_data['product_url'] = str(update_data['product_url'])
                
                # Validate updated data
                merged_data = {
                    'product_url': update_data.get('product_url', product.product_url),
                    'price': update_data.get('price', product.price)
                }
                validate_product_constraints(merged_data)
                
                # Apply updates
                for field, value in update_data.items():
                    setattr(product, field, value)
                
                db.flush()
                logger.debug(f"Updated product fields: {list(update_data.keys())}")
            
    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "UNIQUE constraint failed: products.product_url" in error_msg:
            raise ProductException(
                message="Product URL already exists",
                details={"product_id": product_id, "constraint": "product_url_unique"},
                original_exception=e
            )
        elif "UNIQUE constraint failed: products.sku" in error_msg:
            raise ProductException(
                message="Product SKU already exists",
                details={"product_id": product_id, "constraint": "sku_unique"},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during product update",
                operation="update_product",
                table="products",
                details={"product_id": product_id, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to update product",
            operation="update_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )
    
    try:
        # Return updated product with relationships
        updated_product = db.query(Product).options(
            joinedload(Product.images),
            joinedload(Product.sizes)
        ).filter(Product.id == product_id).first()
        
        logger.info(f"Successfully updated product ID: {product_id}")
        return updated_product
        
    except Exception as e:
        raise DatabaseException(
            message="Failed to retrieve updated product",
            operation="get_product",
            table="products",
            details={"product_id": product_id},
            original_exception=e
        )


def delete_product(db: Session, product_id: int) -> bool:
    """
    Delete a product using soft delete (default behavior for backward compatibility).
    
    Args:
        db: Database session
        product_id: ID of the product to delete
        
    Returns:
        True if deletion was successful
        
    Raises:
        ProductException: If product not found
        DatabaseException: If database operation fails
    """
    from crud.delete_operations import soft_delete_product
    return soft_delete_product(db, product_id)


def get_product_count(db: Session, include_deleted: bool = False) -> int:
    """
    Get the total count of products.
    
    Args:
        db: Database session
        include_deleted: Whether to include soft-deleted products
        
    Returns:
        Total number of products
    """
    try:
        query = db.query(Product)
        
        if not include_deleted:
            query = query.filter(Product.deleted_at.is_(None))
        
        count = query.count()
        logger.debug(f"Total product count: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting product count: {e}")
        raise DatabaseException(
            message="Failed to get product count",
            operation="get_product_count",
            table="products",
            original_exception=e
        )
