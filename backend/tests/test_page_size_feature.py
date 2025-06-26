import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database.session import get_db
from models.product import Base
from schemas.product import ProductCreate

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


def create_test_products(session, count=25):
    """Create test products for pagination testing"""
    products = []
    for i in range(count):
        product_data = ProductCreate(
            product_url=f"https://example.com/product-{i}",
            name=f"Test Product {i}",
            sku=f"TEST-{i:03d}",
            price=10.0 + i,
            currency="USD",
            availability="In Stock",
            color="Blue",
            composition="Cotton",
            item="T-Shirt",
            comment=f"Test product {i}",
        )
        products.append(product_data)
    
    # Import here to avoid circular imports
    from crud.product import create_product
    
    db_products = []
    for product in products:
        db_product = create_product(session, product)
        db_products.append(db_product)
    
    return db_products


class TestPageSizeFeature:
    """Test page size adjustability in pagination"""

    def test_default_page_size_20(self, client, session):
        """Test that default page size is 20"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Get first page with default settings
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["per_page"] == 20
        assert len(data["data"]) == 20
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 2

    def test_page_size_10(self, client, session):
        """Test page size of 10"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Get first page with page size 10
        response = client.get("/api/v1/products?per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["per_page"] == 10
        assert len(data["data"]) == 10
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 3

    def test_page_size_50(self, client, session):
        """Test page size of 50"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Get first page with page size 50
        response = client.get("/api/v1/products?per_page=50")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["per_page"] == 50
        assert len(data["data"]) == 25  # All products fit in one page
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 1

    def test_page_size_100(self, client, session):
        """Test page size of 100"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Get first page with page size 100
        response = client.get("/api/v1/products?per_page=100")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["per_page"] == 100
        assert len(data["data"]) == 25  # All products fit in one page
        assert data["pagination"]["total"] == 25
        assert data["pagination"]["pages"] == 1

    def test_page_size_validation_too_large(self, client, session):
        """Test that page size cannot exceed 100"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Try to get page with size > 100
        response = client.get("/api/v1/products?per_page=150")
        assert response.status_code == 422  # Validation error

    def test_page_size_validation_too_small(self, client, session):
        """Test that page size cannot be less than 1"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Try to get page with size < 1
        response = client.get("/api/v1/products?per_page=0")
        assert response.status_code == 422  # Validation error

    def test_pagination_consistency_across_page_sizes(self, client, session):
        """Test that pagination is consistent across different page sizes"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Test with page size 10
        response_10 = client.get("/api/v1/products?per_page=10&sort_by=id&sort_order=asc")
        assert response_10.status_code == 200
        data_10 = response_10.json()
        
        # Test with page size 25 (all products)
        response_25 = client.get("/api/v1/products?per_page=25&sort_by=id&sort_order=asc")
        assert response_25.status_code == 200
        data_25 = response_25.json()
        
        # First 10 products should be the same
        first_10_from_size_10 = data_10["data"]
        first_10_from_size_25 = data_25["data"][:10]
        
        assert len(first_10_from_size_10) == 10
        assert len(first_10_from_size_25) == 10
        
        # Compare product IDs
        ids_from_10 = [p["id"] for p in first_10_from_size_10]
        ids_from_25 = [p["id"] for p in first_10_from_size_25]
        
        assert ids_from_10 == ids_from_25

    def test_page_size_with_search_and_filters(self, client, session):
        """Test page size works correctly with search and filters"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Search with page size 5
        response = client.get("/api/v1/products?q=Test&per_page=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["pagination"]["per_page"] == 5
        assert len(data["data"]) == 5
        assert data["pagination"]["total"] == 25  # All products match "Test"
        assert data["pagination"]["pages"] == 5

    def test_page_size_persists_across_pages(self, client, session):
        """Test that page size is maintained when navigating between pages"""
        # Create 25 products
        create_test_products(session, 25)
        
        # Get page 1 with size 10
        response_p1 = client.get("/api/v1/products?page=1&per_page=10&sort_by=id&sort_order=asc")
        assert response_p1.status_code == 200
        data_p1 = response_p1.json()
        
        # Get page 2 with size 10
        response_p2 = client.get("/api/v1/products?page=2&per_page=10&sort_by=id&sort_order=asc")
        assert response_p2.status_code == 200
        data_p2 = response_p2.json()
        
        # Both should have the same page size
        assert data_p1["pagination"]["per_page"] == 10
        assert data_p2["pagination"]["per_page"] == 10
        
        # Should have different data
        ids_p1 = [p["id"] for p in data_p1["data"]]
        ids_p2 = [p["id"] for p in data_p2["data"]]
        
        # No overlapping IDs
        assert not set(ids_p1).intersection(set(ids_p2))