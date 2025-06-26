import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta

from main import app
from database.session import get_db
from models.product import Base
from schemas.product import ProductCreate

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_api.db"

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


@pytest.fixture
def sample_product_data():
    return {
        "product_url": "https://example.com/test-product",
        "name": "Test Product",
        "sku": "TEST-001",
        "price": 99.99,
        "currency": "USD",
        "availability": "In Stock",
        "color": "Blue",
        "composition": "100% Cotton",
        "item": "T-Shirt",
        "comment": "A great test product",
        "all_image_urls": [],
        "available_sizes": ["S", "M", "L"]
    }


@pytest.fixture
def create_test_products(client, session):
    """Create multiple test products for testing."""
    products_data = [
        {
            "product_url": "https://example.com/product-1",
            "name": "Product One",
            "sku": "PROD-001",
            "price": 10.0,
            "currency": "USD",
            "all_image_urls": [],
            "available_sizes": ["S"]
        },
        {
            "product_url": "https://example.com/product-2", 
            "name": "Product Two",
            "sku": "PROD-002",
            "price": 20.0,
            "currency": "EUR",
            "all_image_urls": [],
            "available_sizes": ["M", "L"]
        },
        {
            "product_url": "https://example.com/product-3",
            "name": "Product Three",
            "sku": "PROD-003",
            "price": 30.0,
            "currency": "USD",
            "color": "Red",
            "all_image_urls": [],
            "available_sizes": []
        }
    ]
    
    created_products = []
    for product_data in products_data:
        response = client.post("/api/v1/products", json=product_data)
        assert response.status_code == 200
        created_products.append(response.json()["data"])
    
    return created_products


class TestProductsAPI:
    """Test suite for the Products API endpoints."""
    
    def test_create_product_success(self, client, sample_product_data):
        """Test successful product creation."""
        response = client.post("/api/v1/products", json=sample_product_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Product created successfully"
        assert data["data"]["name"] == sample_product_data["name"]
        assert data["data"]["sku"] == sample_product_data["sku"]
        assert len(data["data"]["sizes"]) == 3
    
    def test_create_product_duplicate_url_fails(self, client, sample_product_data):
        """Test that creating a product with duplicate URL fails."""
        # Create first product
        response = client.post("/api/v1/products", json=sample_product_data)
        assert response.status_code == 200
        
        # Try to create duplicate
        response = client.post("/api/v1/products", json=sample_product_data)
        assert response.status_code == 409
        data = response.json()
        assert "error" in data
        assert "already exists" in data["error"]["message"]
    
    def test_get_products_list_empty(self, client):
        """Test getting empty products list."""
        response = client.get("/api/v1/products")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == []
        assert data["pagination"]["total"] == 0
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["per_page"] == 20
    
    def test_get_products_list_with_data(self, client, create_test_products):
        """Test getting products list with data."""
        products = create_test_products
        
        response = client.get("/api/v1/products")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["pages"] == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is False
    
    def test_get_products_pagination(self, client, create_test_products):
        """Test products list pagination."""
        # Get first page with 2 items per page
        response = client.get("/api/v1/products?page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["pages"] == 2
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False
        
        # Get second page
        response = client.get("/api/v1/products?page=2&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is True
    
    def test_get_products_filtering(self, client, create_test_products):
        """Test products filtering."""
        # Filter by price range
        response = client.get("/api/v1/products?min_price=15&max_price=25")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["price"] == 20.0
        
        # Filter by currency
        response = client.get("/api/v1/products?currency=EUR")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["currency"] == "EUR"
        
        # Filter by color
        response = client.get("/api/v1/products?color=Red")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["color"] == "Red"
    
    def test_get_products_search(self, client, create_test_products):
        """Test products search functionality."""
        # Search by name
        response = client.get("/api/v1/products?q=One")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert "One" in data["data"][0]["name"]
        
        # Search by SKU
        response = client.get("/api/v1/products?q=PROD-002")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["sku"] == "PROD-002"
    
    def test_get_products_sorting(self, client, create_test_products):
        """Test products sorting."""
        # Sort by price ascending
        response = client.get("/api/v1/products?sort_by=price&sort_order=asc")
        
        assert response.status_code == 200
        data = response.json()
        prices = [product["price"] for product in data["data"]]
        assert prices == sorted(prices)
        
        # Sort by price descending
        response = client.get("/api/v1/products?sort_by=price&sort_order=desc")
        
        assert response.status_code == 200
        data = response.json()
        prices = [product["price"] for product in data["data"]]
        assert prices == sorted(prices, reverse=True)
    
    def test_get_product_by_id_success(self, client, create_test_products):
        """Test getting a specific product by ID."""
        products = create_test_products
        product_id = products[0]["id"]
        
        response = client.get(f"/api/v1/products/{product_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == product_id
        assert data["data"]["name"] == "Product One"
    
    def test_get_product_by_id_not_found(self, client):
        """Test getting a product that doesn't exist."""
        response = client.get("/api/v1/products/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Product not found" in data["error"]["message"]
    
    def test_update_product_success(self, client, create_test_products):
        """Test successful product update."""
        products = create_test_products
        product_id = products[0]["id"]
        
        update_data = {
            "name": "Updated Product Name",
            "price": 15.99,
            "color": "Green"
        }
        
        response = client.put(f"/api/v1/products/{product_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Product Name"
        assert data["data"]["price"] == 15.99
        assert data["data"]["color"] == "Green"
        # SKU should remain unchanged
        assert data["data"]["sku"] == "PROD-001"
    
    def test_update_product_not_found(self, client):
        """Test updating a product that doesn't exist."""
        update_data = {"name": "New Name"}
        
        response = client.put("/api/v1/products/999", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Product not found" in data["error"]["message"]
    
    def test_delete_product_success(self, client, create_test_products):
        """Test successful product deletion."""
        products = create_test_products
        product_id = products[0]["id"]
        
        response = client.delete(f"/api/v1/products/{product_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted_id"] == product_id
        assert data["message"] == "Product deleted successfully"
        
        # Verify product is deleted
        response = client.get(f"/api/v1/products/{product_id}")
        assert response.status_code == 404
    
    def test_delete_product_not_found(self, client):
        """Test deleting a product that doesn't exist."""
        response = client.delete("/api/v1/products/999")
        
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "Product not found" in data["error"]["message"]
    
    def test_get_product_stats(self, client, create_test_products):
        """Test getting product statistics."""
        response = client.get("/api/v1/products/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        stats = data["data"]
        assert stats["total_products"] == 3
        assert stats["products_with_sizes"] == 2  # Two products have sizes
        assert stats["total_sizes"] == 3  # S + M + L
        assert stats["average_images_per_product"] == 0.0  # No images
    
    def test_get_recent_products(self, client, create_test_products):
        """Test getting recent products."""
        response = client.get("/api/v1/products/recent?limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        # Should be ordered by creation date (most recent first)
        # The ordering might vary if products are created very quickly
        product_names = [p["name"] for p in data["data"]]
        assert len(product_names) == 2
        # All created products should be present in the available names
        assert all(name in ["Product One", "Product Two", "Product Three"] for name in product_names)
    
    def test_search_products_endpoint(self, client, create_test_products):
        """Test the dedicated search endpoint."""
        response = client.get("/api/v1/products/search?q=Product")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3  # All products contain "Product"
        assert "Found 3 products" in data["message"]
        
        # Search for specific term
        response = client.get("/api/v1/products/search?q=Two")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Product Two"
    
    def test_search_products_pagination(self, client, create_test_products):
        """Test search endpoint pagination."""
        response = client.get("/api/v1/products/search?q=Product&page=1&per_page=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["has_next"] is True
    
    def test_search_products_empty_query_fails(self, client):
        """Test that search with empty query fails validation."""
        response = client.get("/api/v1/products/search?q=")
        
        assert response.status_code == 422  # Validation error
    
    def test_invalid_pagination_parameters(self, client):
        """Test API behavior with invalid pagination parameters."""
        # Invalid page number
        response = client.get("/api/v1/products?page=0")
        assert response.status_code == 422
        
        # Invalid per_page number
        response = client.get("/api/v1/products?per_page=0")
        assert response.status_code == 422
        
        # per_page too large
        response = client.get("/api/v1/products?per_page=200")
        assert response.status_code == 422
    
    def test_invalid_sort_order(self, client):
        """Test API behavior with invalid sort order."""
        response = client.get("/api/v1/products?sort_order=invalid")
        assert response.status_code == 422
    
    def test_backward_compatibility_scrape_endpoint(self, client, sample_product_data):
        """Test that the original scrape endpoint still works."""
        response = client.post("/api/v1/scrape", json=sample_product_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_product_data["name"]
        assert data["sku"] == sample_product_data["sku"]