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


def test_no_partial_creation_on_image_integrity_error(db_session):
    image_url = "http://example.com/unique_image.jpg"
    product1_in = ProductCreate(
        product_url="http://example.com/product_with_image",
        name="Product with Image",
        sku="SKU-IMG-1",
        all_image_urls=[image_url],
    )
    create_product(db_session, product1_in)

    product2_url = "http://example.com/another_product"
    product2_in = ProductCreate(
        product_url=product2_url,
        name="Another Product",
        sku="SKU-IMG-2",
        all_image_urls=[image_url],
    )

    with pytest.raises(IntegrityError):
        create_product(db_session, product2_in)
    db_session.rollback()

    db_product = get_product_by_url(db_session, product2_url)
    assert db_product is None


def test_unique_constraints_are_case_sensitive(db_session):
    # Test case-sensitivity for product_url
    product_url = "http://example.com/case_sensitive_test"
    product1_in = ProductCreate(
        product_url=product_url,
        name="Case Test Product 1",
        sku="CASE-SKU-URL",
    )
    create_product(db_session, product1_in)

    # Pydantic's HttpUrl normalizes the domain to lowercase, so we expect the path to be case-sensitive.
    product2_url_case = "HTTP://EXAMPLE.COM/CASE_SENSITIVE_TEST"
    product2_in = ProductCreate(
        product_url=product2_url_case,
        name="Case Test Product 2",
        sku="CASE-SKU-URL-2",
    )
    db_product_2 = create_product(db_session, product2_in)
    assert db_product_2 is not None
    assert db_product_2.product_url == "http://example.com/CASE_SENSITIVE_TEST"

    # Test case-sensitivity for sku
    sku = "UniqueSkuCaseTest"
    product3_in = ProductCreate(
        product_url="http://example.com/case_sensitive_test_3",
        name="Case Test Product 3",
        sku=sku,
    )
    create_product(db_session, product3_in)

    product4_in = ProductCreate(
        product_url="http://example.com/case_sensitive_test_4",
        name="Case Test Product 4",
        sku=sku.lower(),
    )
    db_product_4 = create_product(db_session, product4_in)
    assert db_product_4 is not None
    assert db_product_4.sku == sku.lower()


def test_create_product_with_empty_string_fields(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/empty_fields",
        name="",
        sku="EMPTY-SKU",
        currency="",
        availability="",
        color="",
        composition="",
        item="",
        comment="",
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == ""
    assert db_product.sku == "EMPTY-SKU"
    assert db_product.currency == ""
    assert db_product.availability == ""
    assert db_product.color == ""
    assert db_product.composition == ""
    assert db_product.item == ""
    assert db_product.comment == ""
    assert db_product.price is None


def test_create_product_with_zero_price(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/zero_price",
        name="Zero Price Product",
        sku="ZERO-PRICE-SKU",
        price=0.0,
    )
    db_product = create_product(db_session, product_in)
    assert db_product.price == 0.0


def test_create_product_with_special_characters_and_unicode(db_session):
    product_in = ProductCreate(
        product_url="http://example.com/special_chars",
        name="Product with Special Chars & Unicode 🚀",
        sku="SKU-!@#$%^&*()-+=",
        color="Color-éàç",
        comment="Comment-你好世界",
    )
    db_product = create_product(db_session, product_in)
    assert db_product.name == "Product with Special Chars & Unicode 🚀"
    assert db_product.sku == "SKU-!@#$%^&*()-+="
    assert db_product.color == "Color-éàç"
    assert db_product.comment == "Comment-你好世界"


def test_create_product_with_complex_url(db_session):
    complex_url = "http://example.com/product?id=123&session=abc#details"
    product_in = ProductCreate(
        product_url=complex_url,
        name="Complex URL Product",
        sku="COMPLEX-URL-SKU",
    )
    db_product = create_product(db_session, product_in)
    assert db_product.product_url == complex_url
