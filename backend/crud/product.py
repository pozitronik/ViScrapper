from sqlalchemy.orm import Session, joinedload
from models.product import Product, Image, Size
from schemas.product import ProductCreate
from utils.logger import get_logger
from utils.database import atomic_transaction, validate_product_constraints, bulk_create_relationships

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
    Create a new product with images and sizes in a single atomic transaction with retry logic.
    
    Args:
        db: Database session
        product: Product data to create
        
    Returns:
        Created product with relationships loaded
        
    Raises:
        ValueError: If product data validation fails
        Exception: If database operation fails after retries
    """
    logger.info(f"Creating product: {product.name} ({product.product_url})")
    
    # Validate input data before attempting database operations
    product_dict = product.model_dump()
    validate_product_constraints(product_dict)
    
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

    # After successful commit, load the complete product with relationships
    db_product = db.query(Product).options(
        joinedload(Product.images), 
        joinedload(Product.sizes)
    ).filter(Product.id == db_product.id).first()

    logger.info(f"Successfully created product ID: {db_product.id} with {len(db_product.images)} images and {len(db_product.sizes)} sizes")
    return db_product
