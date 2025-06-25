import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from backend.crud.product import create_product, get_product_by_url
from backend.models.product import Base
from backend.schemas.product import ProductCreate

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def test_create_product(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product",
        name="Test Product",
        sku="TEST-123",
        price=99.99,
        currency="USD",
        all_image_urls=["http://example.com/image1.jpg"],
        available_sizes=["S", "M"],
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == "Test Product"
    assert db_product.sku == "TEST-123"
    assert len(db_product.images) == 1
    assert len(db_product.sizes) == 2


def test_get_product_by_url(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product2",
        name="Test Product 2",
        sku="TEST-456",
    )
    create_product(db_session, product_in)
    db_product = get_product_by_url(db_session, "http://example.com/product2")
    assert db_product is not None
    assert db_product.name == "Test Product 2"


def test_get_product_by_url_not_found(db_session):
    db_product = get_product_by_url(db_session, "http://example.com/nonexistent")
    assert db_product is None


def test_create_product_with_all_fields(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_full",
        name="Test Full Product",
        sku="TEST-FULL-789",
        price=129.99,
        currency="EUR",
        availability="True",
        color="Blue",
        composition="100% Cotton",
        item="T-Shirt",
        comment="A very nice t-shirt",
        all_image_urls=["http://example.com/image_full1.jpg", "http://example.com/image_full2.jpg"],
        available_sizes=["L", "XL"],
    )
    db_product = create_product(db_session, product_in)
    assert db_product.product_url == "http://example.com/product_full"
    assert db_product.name == "Test Full Product"
    assert db_product.sku == "TEST-FULL-789"
    assert db_product.price == 129.99
    assert db_product.currency == "EUR"
    assert db_product.availability == "True"
    assert db_product.color == "Blue"
    assert db_product.composition == "100% Cotton"
    assert db_product.item == "T-Shirt"
    assert db_product.comment == "A very nice t-shirt"
    assert len(db_product.images) == 2
    assert {image.url for image in db_product.images} == {"http://example.com/image_full1.jpg", "http://example.com/image_full2.jpg"}
    assert len(db_product.sizes) == 2
    assert {size.name for size in db_product.sizes} == {"L", "XL"}


def test_create_product_with_no_images_or_sizes(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_minimal",
        name="Test Minimal Product",
        sku="TEST-MIN-000",
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == "Test Minimal Product"
    assert db_product.sku == "TEST-MIN-000"
    assert len(db_product.images) == 0
    assert len(db_product.sizes) == 0


def test_create_product_with_duplicate_url_raises_integrity_error(db_session):
    product1_in = ProductCreate(
        product_url="http://example.com/duplicate_url",
        name="Product 1",
        sku="DUP-URL-1",
    )
    create_product(db_session, product1_in)

    product2_in = ProductCreate(
        product_url="http://example.com/duplicate_url",
        name="Product 2",
        sku="DUP-URL-2",
    )
    with pytest.raises(IntegrityError):
        create_product(db_session, product2_in)


def test_create_product_with_duplicate_sku_raises_integrity_error(db_session):
    product1_in = ProductCreate(
        product_url="http://example.com/product_sku1",
        name="Product SKU 1",
        sku="UNIQUE-SKU-123",
    )
    create_product(db_session, product1_in)

    product2_in = ProductCreate(
        product_url="http://example.com/product_sku2",
        name="Product SKU 2",
        sku="UNIQUE-SKU-123",
    )
    with pytest.raises(IntegrityError):
        create_product(db_session, product2_in)


def test_create_product_with_duplicate_image_urls_raises_integrity_error(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_dup_img",
        name="Product Dup Img",
        sku="DUP-IMG-SKU",
        all_image_urls=["http://example.com/image1.jpg", "http://example.com/image1.jpg"],
    )
    with pytest.raises(IntegrityError):
        create_product(db_session, product_in)


def test_create_product_with_duplicate_sizes(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_dup_size",
        name="Product Dup Size",
        sku="DUP-SIZE-SKU",
        available_sizes=["M", "M"],
    )
    db_product = create_product(db_session, product_in)
    assert len(db_product.sizes) == 2
    assert [size.name for size in db_product.sizes] == ["M", "M"]


def test_create_product_with_images_and_no_sizes(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_img_only",
        name="Product Images Only",
        sku="IMG-ONLY-SKU",
        all_image_urls=["http://example.com/imageA.jpg", "http://example.com/imageB.jpg"],
        available_sizes=[],
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == "Product Images Only"
    assert len(db_product.images) == 2
    assert len(db_product.sizes) == 0


def test_create_product_with_sizes_and_no_images(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/product_size_only",
        name="Product Sizes Only",
        sku="SIZE-ONLY-SKU",
        all_image_urls=[],
        available_sizes=["XL", "XXL"],
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == "Product Sizes Only"
    assert len(db_product.images) == 0
    assert len(db_product.sizes) == 2
