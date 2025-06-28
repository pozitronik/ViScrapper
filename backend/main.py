# Load environment variables from .env file FIRST
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from crud.product import get_product_by_url, create_product, find_existing_product, compare_product_data, update_existing_product_with_changes
from models.product import Base
from schemas.product import Product, ProductCreate
from services.image_downloader import download_images
from services.websocket_service import websocket_manager
from database.session import get_db, engine
from utils.logger import setup_logger, get_logger
from utils.error_handlers import setup_error_handlers
from exceptions.base import ProductException

# Import new API routers
from api.routers.products import router as products_router
from api.routers.health import router as health_router
from api.routers.backup import router as backup_router
from api.routers.templates import router as templates_router
from api.routers.telegram import router as telegram_router
from api.routers.maintenance import router as maintenance_router

# Setup backup service with environment variable support
from services.backup_service import backup_service

# Setup telegram post service for auto-posting
from services.telegram_post_service import telegram_post_service

# Set up logging
setup_logger()
logger = get_logger(__name__)

# Initialize database with migrations instead of create_all
from utils.migrations import initialize_database_with_migrations

# Run migrations on startup
migration_success = initialize_database_with_migrations()
if not migration_success:
    logger.error("Failed to initialize database with migrations. Falling back to create_all()")
    # Fallback to old method if migrations fail
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with proper startup and shutdown"""
    # Startup
    logger.info("Starting VIParser application...")

    # Start scheduled backups if enabled
    if backup_service:
        logger.info("Starting backup service...")
        await backup_service.start_scheduled_backups()
    else:
        logger.info("Backup service disabled via BACKUP_ENABLED=false")

    logger.info("VIParser application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down VIParser application...")

    # Stop scheduled backups if enabled
    if backup_service:
        logger.info("Stopping backup service...")
        await backup_service.stop_scheduled_backups()

    logger.info("VIParser application shut down successfully")


app = FastAPI(
    title="VIParser API",
    description="Comprehensive product scraping and management API with full CRUD operations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up error handlers
setup_error_handlers(app)

# Include API routers
app.include_router(products_router)
app.include_router(health_router)
app.include_router(backup_router)
app.include_router(templates_router)
app.include_router(telegram_router)
app.include_router(maintenance_router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")

            # Echo back or handle specific commands if needed
            await websocket_manager.send_personal_message(
                f"Message received: {data}", websocket
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket disconnected")


@app.post("/api/v1/scrape", response_model=Product)
async def scrape_product(product: ProductCreate, db: Session = Depends(get_db)):
    """
    Scrape and store product information with images.
    Now handles existing products by checking for differences and updating when needed.
    
    Args:
        product: Product data to scrape and store
        db: Database session
    
    Returns:
        Created or updated product with images and sizes
    
    Raises:
        ValidationException: If product data is invalid
        ExternalServiceException: If image download fails
        DatabaseException: If database operation fails
    """
    logger.info(f"Starting product scrape for URL: {product.product_url}")

    # Check if product already exists by URL or SKU
    existing_result = find_existing_product(db, url=str(product.product_url), sku=product.sku)
    existing_product = existing_result['product']
    match_type = existing_result['match_type']

    if existing_product:
        logger.info(f"Found existing product (match: {match_type}) with ID: {existing_product.id}")
        
        # Compare the existing product with new data
        changes = compare_product_data(existing_product, product)
        
        if changes['has_changes']:
            logger.info(f"Differences detected for product {existing_product.id}, updating...")
            
            # Download new images first if there are any
            downloaded_images_metadata = []
            if product.all_image_urls:
                logger.info(f"Downloading {len(product.all_image_urls)} images for product update: {product.product_url}")
                downloaded_images_metadata = await download_images(product.all_image_urls)
                # Replace image URLs with local IDs for storage
                product.all_image_urls = [img['image_id'] if isinstance(img, dict) else img for img in downloaded_images_metadata]
            
            # Update the existing product with changes
            updated_product, update_summary = await update_existing_product_with_changes(
                db, existing_product, product, changes, 
                download_new_images=bool(downloaded_images_metadata),
                downloaded_images_metadata=downloaded_images_metadata
            )
            
            # Broadcast the updated product to all connected WebSocket clients
            from schemas.product import Product as ProductSchema
            product_dict = ProductSchema.model_validate(updated_product).model_dump()
            # Add update information for frontend
            product_dict['_update_info'] = {
                'was_updated': True,
                'match_type': match_type,
                'update_summary': update_summary
            }
            await websocket_manager.broadcast_product_updated(product_dict)
            
            logger.info(f"Successfully updated existing product {existing_product.id} with summary: {update_summary}")
            return updated_product
        else:
            logger.info(f"No changes detected for existing product {existing_product.id}")
            # Still broadcast to frontend with info that no changes were needed
            from schemas.product import Product as ProductSchema
            product_dict = ProductSchema.model_validate(existing_product).model_dump()
            product_dict['_update_info'] = {
                'was_updated': False,
                'match_type': match_type,
                'message': 'Product already exists with identical data'
            }
            await websocket_manager.broadcast_product_updated(product_dict)
            return existing_product

    # No existing product found - create new one
    logger.info(f"No existing product found, creating new product for: {product.product_url}")
    
    # Download images and get their local IDs
    downloaded_images_metadata = []
    if product.all_image_urls:
        logger.info(f"Downloading {len(product.all_image_urls)} images for new product: {product.product_url}")
        downloaded_images_metadata = await download_images(product.all_image_urls)
        # Replace image URLs with local IDs for storage
        product.all_image_urls = [img['image_id'] if isinstance(img, dict) else img for img in downloaded_images_metadata]

    logger.info(f"Creating product in database: {product.product_url}")
    created_product = create_product(db=db, product=product, downloaded_images_metadata=downloaded_images_metadata)

    # Broadcast the new product to all connected WebSocket clients
    from schemas.product import Product as ProductSchema
    product_dict = ProductSchema.model_validate(created_product).model_dump()
    product_dict['_update_info'] = {
        'was_updated': False,
        'match_type': None,
        'message': 'New product created'
    }
    await websocket_manager.broadcast_product_created(product_dict)

    # Auto-post to telegram channels if configured
    try:
        auto_post_result = await telegram_post_service.auto_post_product(db=db, product_id=created_product.id)
        if auto_post_result["success_count"] > 0:
            logger.info(f"Auto-posted product {created_product.id} to {auto_post_result['success_count']} telegram channels")
        elif auto_post_result["failed_count"] > 0:
            logger.warning(f"Failed to auto-post product {created_product.id} to {auto_post_result['failed_count']} telegram channels")
    except Exception as e:
        logger.error(f"Error auto-posting product {created_product.id} to telegram: {e}")
        # Don't fail the main product creation if telegram auto-post fails

    logger.info(f"Successfully created product with ID: {created_product.id} for URL: {product.product_url}")
    return created_product


# Frontend serving routes
import os

if os.path.exists("images"):
    app.mount("/images", StaticFiles(directory="images"), name="images")

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main frontend HTML page"""
    return FileResponse("frontend/index.html")


@app.get("/product/{product_id}")
async def serve_product_page(product_id: int):
    """Serve the product detail HTML page"""
    return FileResponse("frontend/product.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
