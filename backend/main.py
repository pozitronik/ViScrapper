from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from crud.product import get_product_by_url, create_product
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

# Setup backup service with environment variable support
from services.backup_service import backup_service

# Set up logging
setup_logger()
logger = get_logger(__name__)

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
    
    # Broadcast the new product to all connected WebSocket clients
    from schemas.product import Product as ProductSchema
    product_dict = ProductSchema.from_orm(created_product).dict()
    await websocket_manager.broadcast_product_created(product_dict)
    
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )