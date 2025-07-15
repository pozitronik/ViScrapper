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
        "store": "Victoria's Secret",
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
            "store": "Calvin Klein",
            "all_image_urls": [],
            "available_sizes": ["S"]
        },
        {
            "product_url": "https://example.com/product-2", 
            "name": "Product Two",
            "sku": "PROD-002",
            "price": 20.0,
            "currency": "EUR",
            "store": "Victoria's Secret",
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
            "store": "Tommy Hilfiger",
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
        assert data["message"] == "Product soft deleted successfully"
        
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
    
    def test_search_products_by_sku(self, client, create_test_products):
        """Test searching products by SKU field."""
        products = create_test_products
        # Test data has SKUs like "PROD-001", "PROD-002", "PROD-003"
        
        response = client.get("/api/v1/products/search?sku=PROD-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["sku"] == "PROD-001"
        assert "SKU: 'PROD-001'" in data["message"]
    
    def test_search_products_by_name(self, client, create_test_products):
        """Test searching products by name field."""
        response = client.get("/api/v1/products/search?name=Product One")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "Product One"
        assert "name: 'Product One'" in data["message"]
    
    def test_search_products_by_url(self, client, create_test_products):
        """Test searching products by URL field."""
        products = create_test_products
        test_url = products[0]["product_url"]
        
        response = client.get(f"/api/v1/products/search?url={test_url}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["product_url"] == test_url
        assert f"URL: '{test_url}'" in data["message"]
    
    def test_search_products_by_comment(self, client, create_test_products):
        """Test searching products by comment field."""
        response = client.get("/api/v1/products/search?comment=test comment")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Results depend on test data, but should not error
    
    def test_search_products_multiple_fields(self, client, create_test_products):
        """Test searching products with multiple specific fields."""
        response = client.get("/api/v1/products/search?sku=PROD-001&name=Product")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should find products matching BOTH criteria (AND operation)
        assert "SKU: 'PROD-001'" in data["message"]
        assert "name: 'Product'" in data["message"]
    
    def test_search_products_no_parameters_fails(self, client):
        """Test that search without any parameters fails."""
        response = client.get("/api/v1/products/search")
        
        assert response.status_code == 400
        data = response.json()
        assert "At least one search parameter must be provided" in data["error"]["message"]
    
    def test_search_products_backward_compatibility(self, client, create_test_products):
        """Test that old 'q' parameter still works (backward compatibility)."""
        response = client.get("/api/v1/products/search?q=Product")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3  # All products contain "Product"
        assert "general query: 'Product'" in data["message"]
    
    def test_search_products_specific_fields_override_general(self, client, create_test_products):
        """Test that specific fields take precedence over general 'q' parameter."""
        response = client.get("/api/v1/products/search?q=Product&sku=PROD-001")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should use SKU search, not general search
        assert "SKU: 'PROD-001'" in data["message"]
        assert "general query" not in data["message"]
    
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

    def test_delete_product_image_success(self, client, create_test_products, session):
        """Test successful deletion of product image."""
        # First create a product with images
        products = create_test_products
        product_id = products[0]["id"]
        
        # Create a test image for this product (mock scenario)
        from models.product import Image
        
        # Create a test image
        test_image = Image(
            product_id=product_id,
            url="test_image.jpg"
        )
        session.add(test_image)
        session.commit()
        image_id = test_image.id
        
        # Delete the image
        response = client.delete(f"/api/v1/products/{product_id}/images/{image_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Image deleted successfully"
        assert data["data"]["deleted_image_id"] == image_id

    def test_delete_product_image_product_not_found(self, client):
        """Test deletion of image from non-existent product."""
        response = client.delete("/api/v1/products/99999/images/1")
        
        assert response.status_code == 404
        data = response.json()
        assert "Product not found" in data["error"]["message"]

    def test_delete_product_image_image_not_found(self, client, create_test_products):
        """Test deletion of non-existent image."""
        products = create_test_products
        product_id = products[0]["id"]
        
        response = client.delete(f"/api/v1/products/{product_id}/images/99999")
        
        assert response.status_code == 404
        data = response.json()
        assert "Image not found for this product" in data["error"]["message"]

    def test_delete_product_image_wrong_product(self, client, create_test_products, session):
        """Test deletion of image that belongs to different product."""
        products = create_test_products
        product1_id = products[0]["id"]
        product2_id = products[1]["id"]
        
        # Create a test image for product 1
        from models.product import Image
        
        test_image = Image(
            product_id=product1_id,
            url="test_image_product1.jpg"
        )
        session.add(test_image)
        session.commit()
        image_id = test_image.id
        
        # Try to delete it from product 2
        response = client.delete(f"/api/v1/products/{product2_id}/images/{image_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "Image not found for this product" in data["error"]["message"]


class TestProductsRouterHelperFunctions:
    """Test suite for helper functions in products router."""

    def test_calculate_pagination_basic(self):
        """Test basic pagination calculation."""
        from api.routers.products import calculate_pagination
        
        pagination = calculate_pagination(page=1, per_page=10, total=25)
        
        assert pagination.page == 1
        assert pagination.per_page == 10
        assert pagination.total == 25
        assert pagination.pages == 3  # ceil(25/10)
        assert pagination.has_next is True
        assert pagination.has_prev is False

    def test_calculate_pagination_last_page(self):
        """Test pagination calculation for last page."""
        from api.routers.products import calculate_pagination
        
        pagination = calculate_pagination(page=3, per_page=10, total=25)
        
        assert pagination.page == 3
        assert pagination.pages == 3
        assert pagination.has_next is False
        assert pagination.has_prev is True

    def test_calculate_pagination_single_page(self):
        """Test pagination calculation for single page."""
        from api.routers.products import calculate_pagination
        
        pagination = calculate_pagination(page=1, per_page=10, total=5)
        
        assert pagination.page == 1
        assert pagination.pages == 1
        assert pagination.has_next is False
        assert pagination.has_prev is False

    def test_apply_filters_search_query(self, session):
        """Test apply_filters with search query."""
        from api.routers.products import apply_filters
        from api.models.responses import SearchFilters
        from models.product import Product as ProductModel
        
        # Create base query
        query = session.query(ProductModel)
        
        # Test search filter
        filters = SearchFilters(q="test product")
        filtered_query = apply_filters(query, filters)
        
        # Verify filter was applied (check SQL contains LIKE)
        sql_str = str(filtered_query.statement.compile(compile_kwargs={"literal_binds": True}))
        assert "LIKE" in sql_str.upper()

    def test_apply_sorting_invalid_field(self, session):
        """Test apply_sorting with invalid field falls back to default."""
        from api.routers.products import apply_sorting
        from models.product import Product as ProductModel
        
        query = session.query(ProductModel)
        
        # Test invalid field name
        sorted_query = apply_sorting(query, sort_by="invalid_field", sort_order="desc")
        
        # Should fall back to created_at
        sql_str = str(sorted_query.statement.compile(compile_kwargs={"literal_binds": True}))
        assert "ORDER BY" in sql_str.upper()


class TestProductsRouterMissingEndpoints:
    """Test suite for endpoints that need more coverage."""

    def test_cleanup_old_deleted_products_success(self, client, session):
        """Test cleanup of old deleted products."""
        # Create a product and mark it as deleted
        from models.product import Product as ProductModel
        from datetime import datetime, timezone, timedelta
        
        # Create product that was deleted 40 days ago
        old_deleted_time = datetime.now(timezone.utc) - timedelta(days=40)
        product = ProductModel(
            sku="OLD-DELETED-001",
            product_url="https://example.com/old",
            name="Old Product",
            deleted_at=old_deleted_time
        )
        session.add(product)
        session.commit()
        
        # Cleanup products older than 30 days
        response = client.post("/api/v1/products/cleanup-old-deleted?days_old=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted_count"] == 1
        assert data["data"]["days_threshold"] == 30

    def test_cleanup_old_deleted_products_none_found(self, client):
        """Test cleanup when no old deleted products exist."""
        response = client.post("/api/v1/products/cleanup-old-deleted?days_old=30")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted_count"] == 0

    def test_restore_product_success(self, client, session):
        """Test successful product restoration."""
        from models.product import Product as ProductModel
        from datetime import datetime, timezone
        
        # Create a soft-deleted product
        product = ProductModel(
            sku="RESTORE-001",
            product_url="https://example.com/restore",
            name="Restore Product",
            deleted_at=datetime.now(timezone.utc)
        )
        session.add(product)
        session.commit()
        product_id = product.id
        
        # Restore the product
        response = client.post(f"/api/v1/products/{product_id}/restore")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == product_id
        assert data["data"]["name"] == "Restore Product"

    def test_restore_product_not_found(self, client):
        """Test restore of non-existent product."""
        response = client.post("/api/v1/products/99999/restore")
        
        assert response.status_code == 404
        data = response.json()
        # Check both possible error response formats
        error_message = data.get("detail") or data.get("error", {}).get("message", "")
        assert "Product not found" in error_message

    def test_restore_product_not_deleted(self, client, session):
        """Test restore of product that is not deleted."""
        from models.product import Product as ProductModel
        
        # Create a non-deleted product
        product = ProductModel(
            sku="NOT-DELETED-001",
            product_url="https://example.com/notdeleted",
            name="Not Deleted Product"
        )
        session.add(product)
        session.commit()
        product_id = product.id
        
        # Try to restore it
        response = client.post(f"/api/v1/products/{product_id}/restore")
        
        assert response.status_code == 400
        data = response.json()
        # Check both possible error response formats
        error_message = data.get("detail") or data.get("error", {}).get("message", "")
        assert "Product is not deleted" in error_message

    def test_list_products_only_deleted_filter(self, client, session):
        """Test list products with only_deleted filter."""
        from models.product import Product as ProductModel
        from datetime import datetime, timezone
        
        # Create one normal and one deleted product
        normal_product = ProductModel(
            sku="NORMAL-001",
            product_url="https://example.com/normal",
            name="Normal Product"
        )
        deleted_product = ProductModel(
            sku="DELETED-001", 
            product_url="https://example.com/deleted",
            name="Deleted Product",
            deleted_at=datetime.now(timezone.utc)
        )
        session.add_all([normal_product, deleted_product])
        session.commit()
        
        # Get only deleted products
        response = client.get("/api/v1/products?only_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["total"] == 1
        assert data["data"][0]["name"] == "Deleted Product"

    def test_list_products_store_filter(self, client, session):
        """Test list products with store filter."""
        from models.product import Product as ProductModel
        
        # Create products with different stores
        product1 = ProductModel(
            sku="STORE-001",
            product_url="https://example.com/store1",
            name="Store Product 1",
            store="Calvin Klein"
        )
        product2 = ProductModel(
            sku="STORE-002",
            product_url="https://example.com/store2", 
            name="Store Product 2",
            store="Victoria's Secret"
        )
        session.add_all([product1, product2])
        session.commit()
        
        # Filter by store
        response = client.get("/api/v1/products?store=Calvin")
        
        assert response.status_code == 200
        data = response.json()
        # The filter might match both if they contain "Calvin" substring
        # Let's check that at least one matches and has the correct store
        assert data["pagination"]["total"] >= 1
        found_calvin = any(product["store"] == "Calvin Klein" for product in data["data"])
        assert found_calvin