from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from crud.product import get_product_by_url, create_product
from models.product import Base
from schemas.product import Product, ProductCreate
from services.image_downloader import download_images
from database.session import get_db, engine
from utils.logger import setup_logger, get_logger

# Set up logging
setup_logger()
logger = get_logger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="VIParser API", description="Product scraping and management API")


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
        HTTPException: If product already exists or creation fails
    """
    logger.info(f"Starting product scrape for URL: {product.product_url}")
    
    try:
        # Check if product already exists
        db_product = get_product_by_url(db, url=str(product.product_url))
        if db_product:
            logger.warning(f"Product already exists for URL: {product.product_url}")
            raise HTTPException(status_code=400, detail="Product already exists")

        # Download images and get their local IDs
        logger.info(f"Downloading {len(product.all_image_urls)} images for product: {product.product_url}")
        image_ids = await download_images(product.all_image_urls)

        # Replace image URLs with local IDs for storage
        product.all_image_urls = image_ids
        
        logger.info(f"Creating product in database: {product.product_url}")
        created_product = create_product(db=db, product=product)
        
        logger.info(f"Successfully created product with ID: {created_product.id} for URL: {product.product_url}")
        return created_product
        
    except HTTPException:
        # Re-raise HTTPExceptions (they're already handled)
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating product for URL {product.product_url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during product creation")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
