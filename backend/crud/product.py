from sqlalchemy.orm import Session
from backend.models.product import Product, Image, Size
from backend.schemas.product import ProductCreate


def get_product_by_url(db: Session, url: str):
    return db.query(Product).filter(Product.product_url == url).first()


def create_product(db: Session, product: ProductCreate):
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

    for image_url in product.all_image_urls:
        db_product.images.append(Image(url=str(image_url)))

    for size_name in product.available_sizes:
        db_product.sizes.append(Size(name=size_name))

    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
