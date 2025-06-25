from sqlalchemy.orm import Session
from models import product as models_product
from schemas import product as schemas_product

def get_product_by_url(db: Session, url: str):
    return db.query(models_product.Product).filter(models_product.Product.product_url == url).first()

def create_product(db: Session, product: schemas_product.ProductCreate):
    db_product = models_product.Product(
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

    for image_url in product.all_image_urls:
        db_image = models_product.Image(url=str(image_url), product_id=db_product.id)
        db.add(db_image)
    
    for size_name in product.available_sizes:
        db_size = models_product.Size(name=size_name, product_id=db_product.id)
        db.add(db_size)

    db.commit()
    db.refresh(db_product)
    return db_product
