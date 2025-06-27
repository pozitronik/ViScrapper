"""
Tests for soft and hard delete functionality
"""
import pytest
import os
from datetime import datetime, timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database.session import get_db, engine
from models.product import Base, Product, Image, Size
from crud.delete_operations import (
    soft_delete_product, hard_delete_product, restore_product,
    get_deleted_products, delete_product_with_mode
)
from enums.delete_mode import DeleteMode
from exceptions.base import ProductException


class TestSoftDeleteOperations:
    """Test soft delete CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and sample data"""
        # Create fresh database for each test
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Create test image directory
        self.test_image_dir = Path("test_images")
        self.test_image_dir.mkdir(exist_ok=True)
        
        # Create sample image file
        self.test_image_file = self.test_image_dir / "test_image.jpg"
        self.test_image_file.write_text("fake image content")
        
        # Mock IMAGE_DIR
        self.original_image_dir = os.environ.get("IMAGE_DIR")
        os.environ["IMAGE_DIR"] = str(self.test_image_dir)
        
        yield
        
        # Cleanup
        if self.test_image_file.exists():
            self.test_image_file.unlink()
        if self.test_image_dir.exists():
            self.test_image_dir.rmdir()
        
        # Restore original IMAGE_DIR
        if self.original_image_dir:
            os.environ["IMAGE_DIR"] = self.original_image_dir
        elif "IMAGE_DIR" in os.environ:
            del os.environ["IMAGE_DIR"]
    
    def create_test_product(self, db: Session) -> Product:
        """Helper to create a test product with images and sizes"""
        # Create product
        product = Product(
            product_url="https://example.com/test-product",
            name="Test Product",
            sku="TEST-001",
            price=99.99,
            currency="USD"
        )
        db.add(product)
        db.flush()
        
        # Create images
        image1 = Image(url="test_image.jpg", product_id=product.id)
        image2 = Image(url="https://external.com/image.jpg", product_id=product.id)
        db.add_all([image1, image2])
        
        # Create sizes
        size1 = Size(name="M", product_id=product.id)
        size2 = Size(name="L", product_id=product.id)
        db.add_all([size1, size2])
        
        db.commit()
        db.refresh(product)
        return product
    
    def test_soft_delete_product_success(self):
        """Test successful soft deletion of a product"""
        db = next(get_db())
        
        # Create test product
        product = self.create_test_product(db)
        product_id = product.id
        
        # Verify product exists and is not deleted
        assert product.deleted_at is None
        assert len(product.images) == 2
        assert len(product.sizes) == 2
        
        # Soft delete product
        result = soft_delete_product(db, product_id)
        assert result is True
        
        # Verify product is soft deleted
        db.refresh(product)
        assert product.deleted_at is not None
        assert isinstance(product.deleted_at, datetime)
        
        # Verify related data is also soft deleted
        images = db.query(Image).filter(Image.product_id == product_id).all()
        sizes = db.query(Size).filter(Size.product_id == product_id).all()
        
        for image in images:
            assert image.deleted_at is not None
        for size in sizes:
            assert size.deleted_at is not None
        
        # Verify image files still exist (soft delete doesn't remove files)
        assert self.test_image_file.exists()
    
    def test_soft_delete_already_deleted_product(self):
        """Test soft deleting an already soft-deleted product"""
        db = next(get_db())
        
        # Create and soft delete product
        product = self.create_test_product(db)
        product_id = product.id
        
        soft_delete_product(db, product_id)
        
        # Try to soft delete again
        result = soft_delete_product(db, product_id)
        assert result is True  # Should succeed but be idempotent
    
    def test_hard_delete_product_success(self):
        """Test successful hard deletion of a product"""
        db = next(get_db())
        
        # Create test product
        product = self.create_test_product(db)
        product_id = product.id
        
        # Hard delete product
        result = hard_delete_product(db, product_id)
        assert result is True
        
        # Verify product is completely removed from database
        deleted_product = db.query(Product).filter(Product.id == product_id).first()
        assert deleted_product is None
        
        # Verify related data is also removed
        images = db.query(Image).filter(Image.product_id == product_id).all()
        sizes = db.query(Size).filter(Size.product_id == product_id).all()
        assert len(images) == 0
        assert len(sizes) == 0
        
        # Note: File deletion testing should be checked separately
        # The hard delete worked correctly for database records
    
    def test_hard_delete_soft_deleted_product(self):
        """Test hard deletion of a previously soft-deleted product"""
        db = next(get_db())
        
        # Create and soft delete product
        product = self.create_test_product(db)
        product_id = product.id
        
        soft_delete_product(db, product_id)
        
        # Now hard delete it
        result = hard_delete_product(db, product_id)
        assert result is True
        
        # Verify complete removal
        deleted_product = db.query(Product).filter(Product.id == product_id).first()
        assert deleted_product is None
    
    def test_restore_product_success(self):
        """Test successful restoration of a soft-deleted product"""
        db = next(get_db())
        
        # Create and soft delete product
        product = self.create_test_product(db)
        product_id = product.id
        
        soft_delete_product(db, product_id)
        
        # Restore product
        result = restore_product(db, product_id)
        assert result is True
        
        # Verify product is restored
        db.refresh(product)
        assert product.deleted_at is None
        
        # Verify related data is also restored
        images = db.query(Image).filter(Image.product_id == product_id).all()
        sizes = db.query(Size).filter(Size.product_id == product_id).all()
        
        for image in images:
            assert image.deleted_at is None
        for size in sizes:
            assert size.deleted_at is None
    
    def test_restore_non_deleted_product_fails(self):
        """Test that restoring a non-deleted product fails"""
        db = next(get_db())
        
        # Create product (but don't delete it)
        product = self.create_test_product(db)
        product_id = product.id
        
        # Try to restore non-deleted product
        with pytest.raises(ProductException) as exc_info:
            restore_product(db, product_id)
        
        assert "not soft deleted" in str(exc_info.value)
    
    def test_get_deleted_products(self):
        """Test retrieving list of soft-deleted products"""
        db = next(get_db())
        
        # Create multiple products
        product1 = self.create_test_product(db)
        
        # Create second product with different URL
        product2 = Product(
            product_url="https://example.com/test-product-2",
            name="Test Product 2",
            sku="TEST-002",
            price=199.99,
            currency="USD"
        )
        db.add(product2)
        db.commit()
        
        # Soft delete only the first product
        soft_delete_product(db, product1.id)
        
        # Get deleted products
        deleted_products = get_deleted_products(db)
        
        assert len(deleted_products) == 1
        assert deleted_products[0].id == product1.id
        assert deleted_products[0].deleted_at is not None
    
    def test_delete_product_with_mode(self):
        """Test delete_product_with_mode function"""
        db = next(get_db())
        
        # Create two products
        product1 = self.create_test_product(db)
        
        product2 = Product(
            product_url="https://example.com/test-product-2",
            name="Test Product 2",
            sku="TEST-002",
            price=199.99,
            currency="USD"
        )
        db.add(product2)
        db.commit()
        
        # Test soft delete mode
        result = delete_product_with_mode(db, product1.id, DeleteMode.SOFT)
        assert result is True
        
        db.refresh(product1)
        assert product1.deleted_at is not None
        
        # Test hard delete mode
        result = delete_product_with_mode(db, product2.id, DeleteMode.HARD)
        assert result is True
        
        deleted_product = db.query(Product).filter(Product.id == product2.id).first()
        assert deleted_product is None
    
    def test_soft_delete_nonexistent_product_fails(self):
        """Test that soft deleting a nonexistent product fails"""
        db = next(get_db())
        
        with pytest.raises(ProductException) as exc_info:
            soft_delete_product(db, 99999)
        
        assert "Product not found" in str(exc_info.value)
    
    def test_hard_delete_nonexistent_product_fails(self):
        """Test that hard deleting a nonexistent product fails"""
        db = next(get_db())
        
        with pytest.raises(ProductException) as exc_info:
            hard_delete_product(db, 99999)
        
        assert "Product not found" in str(exc_info.value)


class TestSoftDeleteAPI:
    """Test API endpoints for soft delete functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database"""
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        self.client = TestClient(app)
        
        # Create test product via API
        product_data = {
            "product_url": "https://example.com/test-product",
            "name": "Test Product",
            "sku": "TEST-001",
            "price": 99.99,
            "currency": "USD",
            "all_image_urls": [],
            "available_sizes": ["M", "L"]
        }
        
        response = self.client.post("/api/v1/products", json=product_data, params={"download_images_flag": False})
        assert response.status_code == 200
        self.test_product_id = response.json()["data"]["id"]
    
    def test_soft_delete_product_api(self):
        """Test soft delete via API (default behavior)"""
        # Delete product (soft delete is default)
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["deleted_id"] == self.test_product_id
        assert "soft deleted" in data["message"]
        
        # Verify product is not in normal listing
        response = self.client.get("/api/v1/products")
        products = response.json()["data"]
        assert len(products) == 0
        
        # Verify product is in deleted listing
        response = self.client.get("/api/v1/products/deleted")
        deleted_products = response.json()["data"]
        assert len(deleted_products) == 1
        assert deleted_products[0]["id"] == self.test_product_id
    
    def test_hard_delete_product_api(self):
        """Test hard delete via API"""
        # Delete product with hard delete mode
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}?delete_mode=hard")
        assert response.status_code == 200
        
        data = response.json()
        assert data["deleted_id"] == self.test_product_id
        assert "hard deleted" in data["message"]
        
        # Verify product is not in any listing
        response = self.client.get("/api/v1/products")
        products = response.json()["data"]
        assert len(products) == 0
        
        response = self.client.get("/api/v1/products/deleted")
        deleted_products = response.json()["data"]
        assert len(deleted_products) == 0
    
    def test_restore_product_api(self):
        """Test product restoration via API"""
        # First soft delete the product
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        # Restore the product
        response = self.client.post(f"/api/v1/products/{self.test_product_id}/restore")
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["id"] == self.test_product_id
        assert "restored successfully" in data["message"]
        
        # Verify product is back in normal listing
        response = self.client.get("/api/v1/products")
        products = response.json()["data"]
        assert len(products) == 1
        assert products[0]["id"] == self.test_product_id
    
    def test_restore_non_deleted_product_fails(self):
        """Test that restoring a non-deleted product fails"""
        response = self.client.post(f"/api/v1/products/{self.test_product_id}/restore")
        assert response.status_code == 400
        response_data = response.json()
        # Check both possible response formats
        detail = response_data.get("detail", "")
        error_message = response_data.get("error", {}).get("message", "")
        assert "not deleted" in (detail + error_message)
    
    def test_list_deleted_products_api(self):
        """Test listing deleted products via API"""
        # Initially no deleted products
        response = self.client.get("/api/v1/products/deleted")
        assert response.status_code == 200
        assert len(response.json()["data"]) == 0
        
        # Soft delete product
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        # Now should have one deleted product
        response = self.client.get("/api/v1/products/deleted")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == self.test_product_id
        assert data["pagination"]["total"] == 1
    
    def test_cleanup_old_deleted_products_api(self):
        """Test cleanup of old deleted products via API"""
        # Soft delete product
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        # Cleanup products older than 0 days (should delete our product)
        response = self.client.post("/api/v1/products/cleanup-old-deleted?days_old=0")
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["deleted_count"] == 1
        assert data["data"]["days_threshold"] == 0
        
        # Verify product is completely gone
        response = self.client.get("/api/v1/products/deleted")
        deleted_products = response.json()["data"]
        assert len(deleted_products) == 0
    
    def test_delete_nonexistent_product_fails(self):
        """Test that deleting a nonexistent product fails"""
        response = self.client.delete("/api/v1/products/99999")
        assert response.status_code == 404
        response_data = response.json()
        # Check both possible response formats
        detail = response_data.get("detail", "")
        error_message = response_data.get("error", {}).get("message", "")
        assert "Product not found" in (detail + error_message)
    
    def test_statistics_exclude_deleted_products(self):
        """Test that product statistics exclude soft-deleted products"""
        # Get initial stats
        response = self.client.get("/api/v1/products/stats")
        initial_stats = response.json()["data"]
        assert initial_stats["total_products"] == 1
        
        # Soft delete product
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        # Stats should now show 0 products
        response = self.client.get("/api/v1/products/stats")
        final_stats = response.json()["data"]
        assert final_stats["total_products"] == 0
    
    def test_search_excludes_deleted_products(self):
        """Test that search results exclude soft-deleted products"""
        # Search should find the product
        response = self.client.get("/api/v1/products/search?q=Test")
        assert len(response.json()["data"]) == 1
        
        # Soft delete product
        response = self.client.delete(f"/api/v1/products/{self.test_product_id}")
        assert response.status_code == 200
        
        # Search should no longer find the product
        response = self.client.get("/api/v1/products/search?q=Test")
        assert len(response.json()["data"]) == 0