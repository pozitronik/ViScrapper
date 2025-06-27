"""
Tests for message template functionality
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database.session import get_db, engine
from models.product import Base, Product, Image, Size, MessageTemplate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from crud.template import create_template, get_template_by_id, update_template
from schemas.template import MessageTemplateCreate, MessageTemplateUpdate
from services.template_service import template_renderer


class TestMessageTemplates:
    """Test message template CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and sample data"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        yield
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def create_test_product(self, db: Session) -> Product:
        """Helper to create a test product"""
        product = Product(
            product_url="https://example.com/test-product",
            name="Test Product",
            sku="TEST-001",
            price=99.99,
            currency="USD",
            availability="In Stock",
            color="Blue",
            composition="100% Cotton",
            item="T-Shirt",
            comment="A great test product"
        )
        db.add(product)
        
        # Add some images and sizes
        image1 = Image(url="https://example.com/image1.jpg", product_id=None)
        image2 = Image(url="https://example.com/image2.jpg", product_id=None)
        size1 = Size(name="M", product_id=None)
        size2 = Size(name="L", product_id=None)
        
        db.add_all([image1, image2, size1, size2])
        db.commit()
        
        # Update foreign keys
        image1.product_id = product.id
        image2.product_id = product.id
        size1.product_id = product.id
        size2.product_id = product.id
        db.commit()
        
        db.refresh(product)
        return product
    
    def create_test_template(self, db: Session) -> MessageTemplate:
        """Helper to create a test template"""
        template_data = MessageTemplateCreate(
            name="Test Template",
            description="A test template",
            template_content="Product: {product_name} - Price: {product_price} {product_currency}",
            is_active=True
        )
        return create_template(db, template_data)
    
    def test_create_template_success(self):
        """Test successful template creation"""
        db = self.test_db
        
        template_data = MessageTemplateCreate(
            name="Email Template",
            description="Template for email notifications",
            template_content="Check out {product_name} for only {product_price} {product_currency}!",
            is_active=True
        )
        
        template = create_template(db, template_data)
        
        assert template.id is not None
        assert template.name == "Email Template"
        assert template.description == "Template for email notifications"
        assert template.is_active is True
        assert template.created_at is not None
        assert template.updated_at is not None
        assert template.deleted_at is None
    
    def test_create_template_duplicate_name_fails(self):
        """Test that creating template with duplicate name fails"""
        db = self.test_db
        
        # Create first template
        template_data1 = MessageTemplateCreate(
            name="Duplicate Name",
            description="First template",
            template_content="Content 1",
            is_active=True
        )
        create_template(db, template_data1)
        
        # Try to create second template with same name
        template_data2 = MessageTemplateCreate(
            name="Duplicate Name",
            description="Second template",
            template_content="Content 2",
            is_active=True
        )
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            create_template(db, template_data2)
        
        assert "already exists" in str(exc_info.value)
    
    def test_get_template_by_id(self):
        """Test retrieving template by ID"""
        db = self.test_db
        
        # Create template
        created_template = self.create_test_template(db)
        
        # Retrieve template
        retrieved_template = get_template_by_id(db, created_template.id)
        
        assert retrieved_template is not None
        assert retrieved_template.id == created_template.id
        assert retrieved_template.name == "Test Template"
    
    def test_update_template_success(self):
        """Test successful template update"""
        db = self.test_db
        
        # Create template
        template = self.create_test_template(db)
        original_name = template.name
        
        # Update template
        update_data = MessageTemplateUpdate(
            name="Updated Template",
            description="Updated description",
            is_active=False
        )
        
        updated_template = update_template(db, template.id, update_data)
        
        assert updated_template.id == template.id
        assert updated_template.name == "Updated Template"
        assert updated_template.description == "Updated description"
        assert updated_template.is_active is False
        assert updated_template.template_content == template.template_content  # Unchanged


class TestTemplateRenderer:
    """Test template rendering functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and sample data"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        yield
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def create_test_product(self, db: Session) -> Product:
        """Helper to create a test product with images and sizes"""
        product = Product(
            product_url="https://example.com/test-product",
            name="Premium Blue T-Shirt",
            sku="SHIRT-001",
            price=29.99,
            currency="USD",
            availability="In Stock",
            color="Blue",
            composition="100% Cotton",
            item="T-Shirt",
            comment="Comfortable and stylish"
        )
        db.add(product)
        db.commit()
        
        # Add images and sizes
        image1 = Image(url="https://example.com/image1.jpg", product_id=product.id)
        image2 = Image(url="https://example.com/image2.jpg", product_id=product.id)
        size1 = Size(name="M", product_id=product.id)
        size2 = Size(name="L", product_id=product.id)
        
        db.add_all([image1, image2, size1, size2])
        db.commit()
        
        db.refresh(product)
        return product
    
    def test_template_rendering_basic(self):
        """Test basic template rendering with product data"""
        db = self.test_db
        product = self.create_test_product(db)
        
        template_content = "Product: {product_name} - Price: {product_price} {product_currency}"
        
        rendered = template_renderer.render_template(template_content, product)
        
        expected = "Product: Premium Blue T-Shirt - Price: 29.99 USD"
        assert rendered == expected
    
    def test_template_rendering_all_placeholders(self):
        """Test template rendering with all available placeholders"""
        db = self.test_db
        product = self.create_test_product(db)
        
        template_content = """
        Product Details:
        - Name: {product_name}
        - SKU: {product_sku}
        - Price: {product_price} {product_currency}
        - Availability: {product_availability}
        - Color: {product_color}
        - Material: {product_composition}
        - Type: {product_item}
        - Comment: {product_comment}
        - URL: {product_url}
        - ID: {product_id}
        - Images: {product_images_count}
        - Sizes: {product_sizes_count}
        - Available Sizes: {product_sizes}
        - Created: {product_created_at}
        - Generated: {current_date}
        """.strip()
        
        rendered = template_renderer.render_template(template_content, product)
        
        # Check that placeholders were replaced
        assert "{product_name}" not in rendered
        assert "Premium Blue T-Shirt" in rendered
        assert "29.99 USD" in rendered
        assert "M, L" in rendered
        assert "2" in rendered  # Image count
        assert "2" in rendered  # Size count
    
    def test_template_rendering_invalid_placeholder(self):
        """Test that invalid placeholders raise an error"""
        db = self.test_db
        product = self.create_test_product(db)
        
        template_content = "Product: {product_name} - Invalid: {invalid_placeholder}"
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            template_renderer.render_template(template_content, product)
        
        error_details = exc_info.value.details
        assert "invalid placeholders" in str(exc_info.value)
        assert "{invalid_placeholder}" in error_details.get("invalid_placeholders", [])
    
    def test_get_available_placeholders(self):
        """Test getting list of available placeholders"""
        placeholders = template_renderer.get_available_placeholders()
        
        assert isinstance(placeholders, list)
        assert len(placeholders) > 0
        assert "{product_name}" in placeholders
        assert "{product_price}" in placeholders
        assert "{current_date}" in placeholders
    
    def test_extract_placeholders(self):
        """Test extracting placeholders from template content"""
        template_content = "Product {product_name} costs {product_price} {product_currency}"
        
        placeholders = template_renderer.extract_placeholders(template_content)
        
        expected = ["{product_name}", "{product_price}", "{product_currency}"]
        assert placeholders == expected
    
    def test_validate_placeholders(self):
        """Test placeholder validation"""
        # Valid template
        valid_template = "Product {product_name} costs {product_price}"
        invalid_placeholders = template_renderer.validate_placeholders(valid_template)
        assert invalid_placeholders == []
        
        # Invalid template
        invalid_template = "Product {product_name} has {invalid_field}"
        invalid_placeholders = template_renderer.validate_placeholders(invalid_template)
        assert "{invalid_field}" in invalid_placeholders


class TestTemplateAPI:
    """Test template API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        
        # Override dependency injection for isolated testing
        def override_get_db():
            yield self.test_db
        app.dependency_overrides[get_db] = override_get_db
        
        self.client = TestClient(app)
        
        # Create test product
        db = self.test_db
        product = Product(
            product_url="https://example.com/api-test-product",
            name="API Test Product",
            sku="API-001",
            price=49.99,
            currency="USD"
        )
        db.add(product)
        db.commit()
        self.test_product_id = product.id
        
        yield
        
        # Cleanup
        app.dependency_overrides.clear()
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def test_create_template_api(self):
        """Test creating template via API"""
        template_data = {
            "name": "API Template",
            "description": "Created via API",
            "template_content": "Product: {product_name} - Price: {product_price}",
            "is_active": True
        }
        
        response = self.client.post("/api/v1/templates", json=template_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "API Template"
        assert data["data"]["is_active"] is True
    
    def test_get_templates_list_api(self):
        """Test getting templates list via API"""
        # Create a template first
        template_data = {
            "name": "List Test Template",
            "description": "For testing list endpoint",
            "template_content": "Test content",
            "is_active": True
        }
        self.client.post("/api/v1/templates", json=template_data)
        
        # Get templates list
        response = self.client.get("/api/v1/templates")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert data["pagination"]["total"] > 0
    
    def test_template_preview_api(self):
        """Test template preview via API"""
        preview_data = {
            "template_content": "Product: {product_name} - Price: {product_price} {product_currency}",
            "product_id": self.test_product_id
        }
        
        response = self.client.post("/api/v1/templates/preview", json=preview_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "rendered_content" in data
        assert "API Test Product" in data["rendered_content"]
        assert "49.99 USD" in data["rendered_content"]
        assert "available_placeholders" in data
    
    def test_get_available_placeholders_api(self):
        """Test getting available placeholders via API"""
        response = self.client.get("/api/v1/templates/placeholders/available")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "placeholders" in data["data"]
        assert len(data["data"]["placeholders"]) > 0
    
    def test_validate_template_api(self):
        """Test template validation via API"""
        # Valid template
        response = self.client.post("/api/v1/templates/validate?template_content=Product: {product_name}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["is_valid"] is True
        
        # Invalid template
        response = self.client.post("/api/v1/templates/validate?template_content=Product: {invalid_field}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["data"]["is_valid"] is False
        assert len(data["data"]["invalid_placeholders"]) > 0