import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.session import get_db
from models.product import Base
from crud.product import get_product_by_url, get_product_by_sku, create_product

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="session")
def session_fixture():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def client_fixture(session):
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_scrape_product_success(client, session, mocker):
    # Mock the download_images function
    mocker.patch("main.download_images", return_value=["image_id_1", "image_id_2"])

    product_data = {
        "sku": "NEW_PRODUCT_123",
        "product_url": "http://example.com/product/new",
        "name": "New Product",
        "price": 100.0,
        "all_image_urls": ["http://example.com/image/new_1.jpg", "http://example.com/image/new_2.jpg"]
    }
    response = client.post("/api/v1/scrape", json=product_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Product"
    assert data["price"] == 100.0
    
    assert len(data["images"]) == 2
    assert data["images"][0]["url"] == "image_id_1"
    assert data["images"][1]["url"] == "image_id_2"

    # Verify product is in the database
    db_product = get_product_by_sku(session, sku="NEW_PRODUCT_123")
    assert db_product is not None
    assert db_product.name == "New Product"


@pytest.mark.asyncio
async def test_scrape_product_already_exists(client, session, mocker):
    # Create a product in the database first
    existing_product_data = {
        "sku": "EXISTING_PRODUCT_456",
        "product_url": "http://example.com/product/existing",
        "name": "Existing Product",
        "price": 50.0,
        "all_image_urls": ["http://example.com/image/existing_1.jpg"]
    }
    from schemas.product import ProductCreate
    create_product(session, product=ProductCreate(**existing_product_data))

    # Mock the download_images function (though it shouldn't be called in this case)
    mocker.patch("main.download_images", return_value=[])

    product_data = {
        "sku": "EXISTING_PRODUCT_456",
        "product_url": "http://example.com/product/existing",
        "name": "Another Product",
        "price": 75.0,
        "all_image_urls": ["http://example.com/image/another_1.jpg"]
    }
    response = client.post("/api/v1/scrape", json=product_data)

    assert response.status_code == 200  # Should succeed with update
    response_data = response.json()
    assert "id" in response_data  # Should have product ID
    # Should return the existing product (potentially updated) - identified by SKU
    assert response_data["sku"] == "EXISTING_PRODUCT_456"
    # Name should be updated since it's an existing product
    assert response_data["name"] == "Another Product"


@pytest.mark.asyncio
async def test_scrape_product_image_download_failure(client, session, mocker):
    # Mock the download_images function to return an empty list (simulating failure or no images)
    mocker.patch("main.download_images", return_value=[])

    product_data = {
        "sku": "NO_IMAGES_789",
        "product_url": "http://example.com/product/no_images",
        "name": "Product with No Images",
        "price": 25.0,
        "all_image_urls": ["http://example.com/image/no_images_1.jpg"]
    }
    response = client.post("/api/v1/scrape", json=product_data)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Product with No Images"
    assert data["images"] == [] # Expecting an empty list if download fails

    # Verify product is still created in the database, but with no image IDs
    db_product = get_product_by_sku(session, sku="NO_IMAGES_789")
    assert db_product is not None
    assert db_product.images == []
