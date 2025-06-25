from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from models.product import Product, Image, Size
from schemas.product import ProductCreate
from utils.logger import get_logger
from utils.database import atomic_transaction, validate_product_constraints, bulk_create_relationships
from exceptions.base import DatabaseException, ValidationException, ProductException

logger = get_logger(__name__)


def get_product_by_url(db: Session, url: str):
    """
    Get a product by its URL.
    
    Args:
        db: Database session
        url: Product URL to search for
        
    Returns:
        Product instance if found, None otherwise
    """
    logger.debug(f"Searching for product with URL: {url}")
    product = db.query(Product).filter(Product.product_url == url).first()
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
