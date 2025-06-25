from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from crud.product import get_product_by_url, create_product
from models.product import Base
from schemas.product import Product, ProductCreate
from services.image_downloader import download_images
from database.session import get_db, engine
from utils.logger import setup_logger, get_logger
from utils.error_handlers import setup_error_handlers
from exceptions.base import ProductException

# Set up logging
setup_logger()
logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VIParser API", 
    description="Product scraping and management API",
    version="1.0.0"
)

# Set up error handlers
setup_error_handlers(app)


@app.post("/api/v1/scrape", response_model=Product)
async def scrape_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Scrape and store product information with images.
    
    Args:
        product: Product data to scrape and store
        db: Database session
    
    Returns:
        Created product with images and sizes
    
    Raises:
        ProductException: If product already exists
        ValidationException: If product data is invalid
        ExternalServiceException: If image download fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Starting product scrape for URL: {product.product_url}")
    
    # Check if product already exists
    db_product = get_product_by_url(db, url=str(product.product_url))
    if db_product:
        logger.warning(f"Product already exists for URL: {product.product_url}")
        raise ProductException(
            message="Product with this URL already exists",
            product_url=str(product.product_url),
            details={"existing_product_id": db_product.id}
        )

    # Download images and get their local IDs
    logger.info(f"Downloading {len(product.all_image_urls)} images for product: {product.product_url}")
    image_ids = await download_images(product.all_image_urls)

    # Replace image URLs with local IDs for storage
    product.all_image_urls = image_ids
    
    logger.info(f"Creating product in database: {product.product_url}")
    created_product = create_product(db=db, product=product)
    
    logger.info(f"Successfully created product with ID: {created_product.id} for URL: {product.product_url}")
    return created_product


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
