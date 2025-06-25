from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from crud.product import get_product_by_url, create_product
from models.product import Base
from schemas.product import Product, ProductCreate
from services.image_downloader import download_images
from database.session import get_db, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.post("/api/v1/scrape", response_model=Product)
async def scrape_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = get_product_by_url(db, url=str(product.product_url))
    if db_product:
        raise HTTPException(status_code=400, detail="Product already exists")

    # Download images and get their local IDs
    image_ids = await download_images(product.all_image_urls)

    # Replace image URLs with local IDs for storage
    product.all_image_urls = image_ids

    return create_product(db=db, product=product)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
