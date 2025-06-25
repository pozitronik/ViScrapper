import pytest
import tempfile
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.pool import StaticPool
from pydantic_core import ValidationError

from crud.product import create_product
from models.product import Base, Product, Image, Size
from schemas.product import ProductCreate
from utils.database import atomic_transaction, validate_product_constraints, bulk_create_relationships


class TestTransactionManagement:
    """Test transaction management functionality."""
    
    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a fresh database session for each test."""
        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, 
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        Base.metadata.create_all(bind=engine)
        
        session = TestingSessionLocal()
        
        yield session
        
        session.close()
        
    @pytest.fixture(scope="function")
    def constraint_db_session(self):
        """Create a fresh database session for constraint violation tests."""
        SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, 
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        Base.metadata.create_all(bind=engine)
        
        session = TestingSessionLocal()
        
        yield session
        
        session.close()
    
    def test_atomic_transaction_success(self, db_session):
        """Test that atomic transaction commits on success."""
        with atomic_transaction(db_session):
            product = Product(
                product_url="http://example.com/test",
                name="Test Product",
                sku="TEST-123"
            )
            db_session.add(product)
        
        # Verify product was committed
        saved_product = db_session.query(Product).filter_by(sku="TEST-123").first()
        assert saved_product is not None
        assert saved_product.name == "Test Product"
    
    def test_atomic_transaction_rollback_on_exception(self, db_session):
        """Test that atomic transaction rolls back on exception."""
        with pytest.raises(ValueError):
            with atomic_transaction(db_session):
                product = Product(
                    product_url="http://example.com/test",
                    name="Test Product",
                    sku="TEST-123"
                )
                db_session.add(product)
                # Force an exception
                raise ValueError("Test exception")
        
        # Verify product was not committed
        saved_product = db_session.query(Product).filter_by(sku="TEST-123").first()
        assert saved_product is None
    
    def test_atomic_transaction_operational_error_rollback(self, db_session):
        """Test that atomic transaction rolls back on operational errors."""
        # Mock the database session to raise OperationalError
        original_commit = db_session.commit
        
        def mock_commit():
            raise OperationalError("Database connection lost", None, None)
        
        db_session.commit = mock_commit
        
        with pytest.raises(OperationalError):
            with atomic_transaction(db_session):
                product = Product(
                    product_url="http://example.com/test",
                    name="Test Product",
                    sku="TEST-123"
                )
                db_session.add(product)
        
        # Restore original commit for verification query
        db_session.commit = original_commit
        
        # Verify product was not committed due to rollback
        saved_product = db_session.query(Product).filter_by(sku="TEST-123").first()
        assert saved_product is None
    
    def test_validate_product_constraints_valid_data(self):
        """Test that valid product data passes validation."""
        valid_data = {
            'product_url': 'http://example.com/product',
            'name': 'Test Product',
            'price': 99.99
        }
        
        # Should not raise any exception
        validate_product_constraints(valid_data)
    
    def test_validate_product_constraints_missing_url(self):
        """Test validation fails for missing product URL."""
        invalid_data = {
            'name': 'Test Product',
            'price': 99.99
        }
        
        with pytest.raises(ValueError, match="Required field 'product_url' is missing"):
            validate_product_constraints(invalid_data)
    
    def test_validate_product_constraints_empty_url(self):
        """Test validation fails for empty product URL."""
        invalid_data = {
            'product_url': '',
            'name': 'Test Product'
        }
        
        with pytest.raises(ValueError, match="Required field 'product_url' is missing"):
            validate_product_constraints(invalid_data)
    
    def test_validate_product_constraints_invalid_url_format(self):
        """Test validation fails for invalid URL format."""
        invalid_data = {
            'product_url': 'not-a-valid-url',
            'name': 'Test Product'
        }
        
        with pytest.raises(ValueError, match="Invalid product URL format"):
            validate_product_constraints(invalid_data)
    
    def test_validate_product_constraints_negative_price(self):
        """Test validation fails for negative price."""
        invalid_data = {
            'product_url': 'http://example.com/product',
            'name': 'Test Product',
            'price': -10.0
        }
        
        with pytest.raises(ValueError, match="Price cannot be negative"):
            validate_product_constraints(invalid_data)
    
    def test_bulk_create_relationships_images(self, db_session):
        """Test bulk creation of image relationships."""
        # Create a product first
        product = Product(
            product_url="http://example.com/test",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        # Bulk create images
        image_urls = ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]
        bulk_create_relationships(db_session, product.id, image_urls, Image, 'url')
        db_session.commit()
        
        # Verify images were created
        images = db_session.query(Image).filter_by(product_id=product.id).all()
        assert len(images) == 2
        assert {img.url for img in images} == set(image_urls)
    
    def test_bulk_create_relationships_sizes(self, db_session):
        """Test bulk creation of size relationships."""
        # Create a product first
        product = Product(
            product_url="http://example.com/test",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        # Bulk create sizes
        size_names = ["S", "M", "L"]
        bulk_create_relationships(db_session, product.id, size_names, Size, 'name')
        db_session.commit()
        
        # Verify sizes were created
        sizes = db_session.query(Size).filter_by(product_id=product.id).all()
        assert len(sizes) == 3
        assert {size.name for size in sizes} == set(size_names)
    
    def test_bulk_create_relationships_empty_list(self, db_session):
        """Test bulk creation with empty list does nothing."""
        # Create a product first
        product = Product(
            product_url="http://example.com/test",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        # Bulk create with empty list
        bulk_create_relationships(db_session, product.id, [], Image, 'url')
        db_session.commit()
        
        # Verify no images were created
        images = db_session.query(Image).filter_by(product_id=product.id).all()
        assert len(images) == 0
    
    def test_create_product_atomic_transaction(self, db_session):
        """Test that create_product uses atomic transactions properly."""
        product_data = ProductCreate(
            product_url="http://example.com/product",
            name="Test Product",
            sku="TEST-123",
            price=99.99,
            all_image_urls=["http://example.com/img1.jpg", "http://example.com/img2.jpg"],
            available_sizes=["S", "M", "L"]
        )
        
        created_product = create_product(db_session, product_data)
        
        # Verify all data was created atomically
        assert created_product.id is not None
        assert created_product.name == "Test Product"
        assert len(created_product.images) == 2
        assert len(created_product.sizes) == 3
    
    def test_create_product_validation_failure(self, db_session):
        """Test that create_product fails validation for invalid data."""
        # Pydantic will catch this before our custom validation
        with pytest.raises(ValidationError):
            product_data = ProductCreate(
                product_url="invalid-url",  # Invalid URL format
                name="Test Product"
            )
    
    def test_create_product_rollback_on_constraint_violation(self, constraint_db_session):
        """Test that create_product rolls back on database constraint violations."""
        # Create first product
        product_data1 = ProductCreate(
            product_url="http://example.com/product",
            name="Test Product 1",
            sku="UNIQUE-SKU"
        )
        created_product1 = create_product(constraint_db_session, product_data1)
        assert created_product1.sku == "UNIQUE-SKU"
        
        # Try to create second product with same SKU (should fail)
        product_data2 = ProductCreate(
            product_url="http://example.com/product2",
            name="Test Product 2",
            sku="UNIQUE-SKU"  # Duplicate SKU
        )
        
        with pytest.raises(IntegrityError):
            create_product(constraint_db_session, product_data2)
        
        # Verify only first product exists
        products = constraint_db_session.query(Product).all()
        assert len(products) == 1
        assert products[0].name == "Test Product 1"
    
    def test_create_product_partial_failure_rollback(self, constraint_db_session):
        """Test that create_product rolls back if images fail but product succeeds."""
        # Create a product with a duplicate image URL to force integrity error
        product_data1 = ProductCreate(
            product_url="http://example.com/product1",
            name="Test Product 1",
            all_image_urls=["http://example.com/unique_image.jpg"]
        )
        created_product1 = create_product(constraint_db_session, product_data1)
        assert created_product1.name == "Test Product 1"
        
        # Try to create another product with the same image URL
        product_data2 = ProductCreate(
            product_url="http://example.com/product2",
            name="Test Product 2",
            all_image_urls=["http://example.com/unique_image.jpg"]  # Duplicate image URL
        )
        
        with pytest.raises(IntegrityError):
            create_product(constraint_db_session, product_data2)
        
        # Verify second product was completely rolled back
        products = constraint_db_session.query(Product).filter_by(name="Test Product 2").all()
        assert len(products) == 0
        
        # Verify only first product exists
        products = constraint_db_session.query(Product).all()
        assert len(products) == 1
        assert products[0].name == "Test Product 1"