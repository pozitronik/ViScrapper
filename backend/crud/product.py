from sqlalchemy.orm import Session, joinedload
from models.product import Product, Image, Size
from schemas.product import ProductCreate
from utils.logger import get_logger

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
    Create a new product with images and sizes.
    
    Args:
        db: Database session
        product: Product data to create
        
    Returns:
        Created product with relationships loaded
        
    Raises:
        Exception: If database operation fails
    """
    logger.info(f"Creating product: {product.name} ({product.product_url})")
    
    try:
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
        db.commit()
        db.refresh(db_product)
        logger.debug(f"Created product with ID: {db_product.id}")

        # Add images
        if product.all_image_urls:
            logger.info(f"Adding {len(product.all_image_urls)} images to product ID: {db_product.id}")
            for i, image_url in enumerate(product.all_image_urls, 1):
                image = Image(url=str(image_url), product_id=db_product.id)
                db.add(image)
                logger.debug(f"Added image {i}/{len(product.all_image_urls)}: {image_url}")

        # Add sizes
        if product.available_sizes:
            logger.info(f"Adding {len(product.available_sizes)} sizes to product ID: {db_product.id}")
            for i, size_name in enumerate(product.available_sizes, 1):
                size = Size(name=size_name, product_id=db_product.id)
                db.add(size)
                logger.debug(f"Added size {i}/{len(product.available_sizes)}: {size_name}")

        # Commit all changes
        db.commit()
        db.refresh(db_product)

        # Explicitly load the relationships after refresh
        db_product = db.query(Product).options(
            joinedload(Product.images), 
            joinedload(Product.sizes)
        ).filter(Product.id == db_product.id).first()

        logger.info(f"Successfully created product ID: {db_product.id} with {len(db_product.images)} images and {len(db_product.sizes)} sizes")
        return db_product
        
    except Exception as e:
        logger.error(f"Error creating product {product.name} ({product.product_url}): {e}")
        db.rollback()
        raise
