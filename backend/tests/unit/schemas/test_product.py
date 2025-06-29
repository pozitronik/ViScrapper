"""
Comprehensive unit tests for product schemas.

This module contains extensive tests for all product-related Pydantic schemas including
ImageBase, ImageCreate, Image, SizeBase, SizeCreate, Size, ProductBase, ProductCreate, 
ProductUpdate, and Product classes.
"""

import pytest
import os
from unittest.mock import patch
from typing import List, Dict, Any
from pydantic import BaseModel, ValidationError, HttpUrl
from datetime import datetime

from schemas.product import (
    ImageBase, ImageCreate, Image,
    SizeBase, SizeCreate, Size,
    ProductBase, ProductCreate, ProductUpdate, Product
)


class TestImageBase:
    """Test suite for ImageBase schema."""

    def test_image_base_creation(self):
        """Test basic ImageBase creation."""
        image = ImageBase(url="https://example.com/image.jpg")
        
        assert image.url == "https://example.com/image.jpg"

    def test_image_base_with_various_urls(self):
        """Test ImageBase with different URL formats."""
        # HTTP URL
        image1 = ImageBase(url="http://example.com/image.png")
        assert image1.url == "http://example.com/image.png"
        
        # HTTPS URL
        image2 = ImageBase(url="https://cdn.example.com/path/to/image.gif")
        assert image2.url == "https://cdn.example.com/path/to/image.gif"
        
        # URL with query parameters
        image3 = ImageBase(url="https://example.com/image.jpg?size=large&format=webp")
        assert image3.url == "https://example.com/image.jpg?size=large&format=webp"

    def test_image_base_empty_url(self):
        """Test ImageBase with empty URL."""
        image = ImageBase(url="")
        assert image.url == ""

    def test_image_base_serialization(self):
        """Test ImageBase JSON serialization."""
        image = ImageBase(url="https://example.com/test.jpg")
        json_data = image.model_dump()
        
        expected = {"url": "https://example.com/test.jpg"}
        assert json_data == expected

    def test_image_base_deserialization(self):
        """Test ImageBase JSON deserialization."""
        json_data = {"url": "https://example.com/deserialized.jpg"}
        image = ImageBase(**json_data)
        
        assert image.url == "https://example.com/deserialized.jpg"

    def test_image_base_required_field(self):
        """Test that URL field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ImageBase()
        
        assert "url" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)


class TestImageCreate:
    """Test suite for ImageCreate schema."""

    def test_image_create_inheritance(self):
        """Test that ImageCreate inherits from ImageBase."""
        image = ImageCreate(url="https://example.com/create.jpg")
        
        assert isinstance(image, ImageBase)
        assert image.url == "https://example.com/create.jpg"

    def test_image_create_functionality(self):
        """Test ImageCreate specific functionality."""
        image = ImageCreate(url="https://example.com/new-image.png")
        
        # Should have same behavior as ImageBase
        assert image.url == "https://example.com/new-image.png"
        
        # Should serialize properly
        json_data = image.model_dump()
        assert json_data == {"url": "https://example.com/new-image.png"}


class TestImage:
    """Test suite for Image schema."""

    def test_image_full_schema(self):
        """Test complete Image schema with all fields."""
        image = Image(
            id=1,
            product_id=42,
            url="https://example.com/product-image.jpg"
        )
        
        assert image.id == 1
        assert image.product_id == 42
        assert image.url == "https://example.com/product-image.jpg"

    def test_image_inheritance(self):
        """Test that Image inherits from ImageBase."""
        image = Image(id=1, product_id=2, url="https://example.com/test.jpg")
        
        assert isinstance(image, ImageBase)

    def test_image_serialization(self):
        """Test Image JSON serialization."""
        image = Image(id=10, product_id=20, url="https://example.com/serialize.jpg")
        json_data = image.model_dump()
        
        expected = {
            "id": 10,
            "product_id": 20,
            "url": "https://example.com/serialize.jpg"
        }
        assert json_data == expected

    def test_image_required_fields(self):
        """Test that all Image fields are required."""
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            Image(product_id=1, url="https://example.com/test.jpg")
        assert "id" in str(exc_info.value)
        
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            Image(id=1, url="https://example.com/test.jpg")
        assert "product_id" in str(exc_info.value)
        
        # Missing url (inherited requirement)
        with pytest.raises(ValidationError) as exc_info:
            Image(id=1, product_id=1)
        assert "url" in str(exc_info.value)

    def test_image_type_validation(self):
        """Test Image field type validation."""
        # String IDs should be converted to int
        image = Image(id="5", product_id="10", url="https://example.com/test.jpg")
        assert image.id == 5
        assert image.product_id == 10
        
        # Invalid ID types should raise ValidationError
        with pytest.raises(ValidationError):
            Image(id="invalid", product_id=1, url="https://example.com/test.jpg")


class TestSizeBase:
    """Test suite for SizeBase schema."""

    def test_size_base_simple_size(self):
        """Test SizeBase with simple size configuration."""
        size = SizeBase(
            size_type="simple",
            size_value="M"
        )
        
        assert size.size_type == "simple"
        assert size.size_value == "M"
        assert size.size1_type is None
        assert size.size2_type is None
        assert size.combination_data is None

    def test_size_base_combination_size(self):
        """Test SizeBase with combination size configuration."""
        combination_data = {
            "34": ["B", "C"],
            "36": ["A", "B", "C", "D"]
        }
        
        size = SizeBase(
            size_type="combination",
            size1_type="Band",
            size2_type="Cup",
            combination_data=combination_data
        )
        
        assert size.size_type == "combination"
        assert size.size1_type == "Band"
        assert size.size2_type == "Cup"
        assert size.combination_data == combination_data
        assert size.size_value is None

    def test_size_base_minimal(self):
        """Test SizeBase with minimal required data."""
        size = SizeBase(size_type="simple")
        
        assert size.size_type == "simple"
        assert size.size_value is None

    def test_size_base_all_optional_fields(self):
        """Test SizeBase with all optional fields set."""
        size = SizeBase(
            size_type="custom",
            size_value="XL",
            size1_type="Length",
            size2_type="Width",
            combination_data={"42": ["Regular", "Slim"]}
        )
        
        assert size.size_type == "custom"
        assert size.size_value == "XL"
        assert size.size1_type == "Length"
        assert size.size2_type == "Width"
        assert size.combination_data == {"42": ["Regular", "Slim"]}

    def test_size_base_serialization(self):
        """Test SizeBase JSON serialization."""
        size = SizeBase(
            size_type="combination",
            size1_type="Band",
            size2_type="Cup",
            combination_data={"34": ["B"]}
        )
        
        json_data = size.model_dump()
        expected = {
            "size_type": "combination",
            "size_value": None,
            "size1_type": "Band",
            "size2_type": "Cup",
            "combination_data": {"34": ["B"]}
        }
        assert json_data == expected

    def test_size_base_required_field(self):
        """Test that size_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            SizeBase()
        
        assert "size_type" in str(exc_info.value)
        assert "Field required" in str(exc_info.value)


class TestSizeCreate:
    """Test suite for SizeCreate schema."""

    def test_size_create_inheritance(self):
        """Test that SizeCreate inherits from SizeBase."""
        size = SizeCreate(size_type="simple", size_value="L")
        
        assert isinstance(size, SizeBase)
        assert size.size_type == "simple"
        assert size.size_value == "L"


class TestSize:
    """Test suite for Size schema."""

    def test_size_full_schema(self):
        """Test complete Size schema."""
        size = Size(
            id=1,
            product_id=42,
            size_type="simple",
            size_value="M"
        )
        
        assert size.id == 1
        assert size.product_id == 42
        assert size.size_type == "simple"
        assert size.size_value == "M"

    def test_size_with_combination(self):
        """Test Size schema with combination data."""
        combination_data = {"S": ["Short", "Regular"], "M": ["Regular", "Long"]}
        
        size = Size(
            id=2,
            product_id=43,
            size_type="combination",
            size1_type="Size",
            size2_type="Length",
            combination_data=combination_data
        )
        
        assert size.id == 2
        assert size.product_id == 43
        assert size.size_type == "combination"
        assert size.combination_data == combination_data

    def test_size_required_fields(self):
        """Test Size required fields validation."""
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            Size(product_id=1, size_type="simple")
        assert "id" in str(exc_info.value)
        
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            Size(id=1, size_type="simple")
        assert "product_id" in str(exc_info.value)


class TestProductBase:
    """Test suite for ProductBase schema."""

    def test_product_base_minimal(self):
        """Test ProductBase with minimal required data."""
        product = ProductBase(product_url="https://example.com/product/123")
        
        assert str(product.product_url) == "https://example.com/product/123"
        assert product.name is None
        assert product.sku is None
        assert product.price is None

    def test_product_base_full(self):
        """Test ProductBase with all fields."""
        product = ProductBase(
            product_url="https://shop.example.com/item/456",
            name="Test Product",
            sku="SKU123",
            price=29.99,
            currency="USD",
            availability="In Stock",
            color="Blue",
            composition="100% Cotton",
            item="T-Shirt",
            comment="Great product"
        )
        
        assert str(product.product_url) == "https://shop.example.com/item/456"
        assert product.name == "Test Product"
        assert product.sku == "SKU123"
        assert product.price == 29.99
        assert product.currency == "USD"
        assert product.availability == "In Stock"
        assert product.color == "Blue"
        assert product.composition == "100% Cotton"
        assert product.item == "T-Shirt"
        assert product.comment == "Great product"

    def test_product_base_url_validation(self):
        """Test ProductBase URL validation."""
        # Valid HTTPS URL
        product1 = ProductBase(product_url="https://example.com/product")
        assert str(product1.product_url) == "https://example.com/product"
        
        # Valid HTTP URL
        product2 = ProductBase(product_url="http://localhost:8000/product")
        assert str(product2.product_url) == "http://localhost:8000/product"
        
        # Invalid URL should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            ProductBase(product_url="not-a-url")
        assert "url" in str(exc_info.value).lower()

    def test_product_base_price_types(self):
        """Test ProductBase price field type handling."""
        # Float price
        product1 = ProductBase(product_url="https://example.com/1", price=19.99)
        assert product1.price == 19.99
        
        # Integer price (should be converted to float)
        product2 = ProductBase(product_url="https://example.com/2", price=25)
        assert product2.price == 25.0
        
        # String price (should be converted)
        product3 = ProductBase(product_url="https://example.com/3", price="15.50")
        assert product3.price == 15.50

    def test_product_base_serialization(self):
        """Test ProductBase serialization."""
        product = ProductBase(
            product_url="https://example.com/product",
            name="Test Item",
            price=12.34
        )
        
        json_data = product.model_dump()
        
        # URL should be serialized as string
        assert str(json_data["product_url"]) == "https://example.com/product"
        assert json_data["name"] == "Test Item"
        assert json_data["price"] == 12.34


class TestProductCreate:
    """Test suite for ProductCreate schema."""

    def test_product_create_basic(self):
        """Test basic ProductCreate functionality."""
        product = ProductCreate(
            product_url="https://example.com/new-product",
            name="New Product",
            all_image_urls=["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            available_sizes=["S", "M", "L"]
        )
        
        assert str(product.product_url) == "https://example.com/new-product"
        assert product.name == "New Product"
        assert product.all_image_urls == ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        assert product.available_sizes == ["S", "M", "L"]

    def test_product_create_with_size_combinations(self):
        """Test ProductCreate with size combinations."""
        size_combinations = {
            "size1_type": "Band",
            "size2_type": "Cup",
            "combinations": {
                "34": ["B", "C"],
                "36": ["A", "B", "C"]
            }
        }
        
        product = ProductCreate(
            product_url="https://example.com/bra",
            size_combinations=size_combinations
        )
        
        assert product.size_combinations == size_combinations

    def test_product_create_empty_lists(self):
        """Test ProductCreate with empty lists."""
        product = ProductCreate(
            product_url="https://example.com/product",
            all_image_urls=[],
            available_sizes=[]
        )
        
        assert product.all_image_urls == []
        assert product.available_sizes == []

    def test_product_create_default_values(self):
        """Test ProductCreate default values."""
        product = ProductCreate(product_url="https://example.com/product")
        
        assert product.all_image_urls == []
        assert product.available_sizes == []
        assert product.size_combinations is None

    def test_product_create_inheritance(self):
        """Test that ProductCreate inherits from ProductBase."""
        product = ProductCreate(
            product_url="https://example.com/product",
            name="Inherited Product",
            price=99.99
        )
        
        assert isinstance(product, ProductBase)
        assert product.name == "Inherited Product"
        assert product.price == 99.99


class TestProductUpdate:
    """Test suite for ProductUpdate schema."""

    def test_product_update_all_optional(self):
        """Test that all ProductUpdate fields are optional."""
        # Should be able to create with no fields
        update = ProductUpdate()
        
        assert update.product_url is None
        assert update.name is None
        assert update.sku is None
        assert update.price is None
        assert update.currency is None
        assert update.availability is None
        assert update.color is None
        assert update.composition is None
        assert update.item is None
        assert update.comment is None

    def test_product_update_partial(self):
        """Test ProductUpdate with partial data."""
        update = ProductUpdate(
            name="Updated Name",
            price=49.99,
            color="Red"
        )
        
        assert update.name == "Updated Name"
        assert update.price == 49.99
        assert update.color == "Red"
        assert update.sku is None
        assert update.currency is None

    def test_product_update_full(self):
        """Test ProductUpdate with all fields."""
        update = ProductUpdate(
            product_url="https://example.com/updated-product",
            name="Fully Updated Product",
            sku="UPD123",
            price=79.99,
            currency="EUR",
            availability="Limited",
            color="Green",
            composition="50% Cotton, 50% Polyester",
            item="Updated Item",
            comment="Updated comment"
        )
        
        assert str(update.product_url) == "https://example.com/updated-product"
        assert update.name == "Fully Updated Product"
        assert update.sku == "UPD123"
        assert update.price == 79.99
        assert update.currency == "EUR"
        assert update.availability == "Limited"
        assert update.color == "Green"
        assert update.composition == "50% Cotton, 50% Polyester"
        assert update.item == "Updated Item"
        assert update.comment == "Updated comment"

    def test_product_update_url_validation(self):
        """Test ProductUpdate URL validation."""
        # Valid URL
        update1 = ProductUpdate(product_url="https://example.com/valid")
        assert str(update1.product_url) == "https://example.com/valid"
        
        # Invalid URL should raise ValidationError
        with pytest.raises(ValidationError):
            ProductUpdate(product_url="invalid-url")


class TestProduct:
    """Test suite for Product schema."""

    def test_product_basic(self):
        """Test basic Product schema."""
        now = datetime.now()
        
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            name="Test Product",
            created_at=now,
            images=[],
            sizes=[]
        )
        
        assert product.id == 1
        assert str(product.product_url) == "https://example.com/product/1"
        assert product.name == "Test Product"
        assert product.created_at == now
        assert product.telegram_posted_at is None
        assert product.images == []
        assert product.sizes == []

    def test_product_with_images_and_sizes(self):
        """Test Product with images and sizes."""
        now = datetime.now()
        
        images = [
            Image(id=1, product_id=1, url="https://example.com/img1.jpg"),
            Image(id=2, product_id=1, url="https://example.com/img2.jpg")
        ]
        
        sizes = [
            Size(id=1, product_id=1, size_type="simple", size_value="M"),
            Size(id=2, product_id=1, size_type="simple", size_value="L")
        ]
        
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            name="Product with Images and Sizes",
            created_at=now,
            telegram_posted_at=now,
            images=images,
            sizes=sizes,
            price=25.00
        )
        
        assert len(product.images) == 2
        assert len(product.sizes) == 2
        assert product.images[0].url == "https://example.com/img1.jpg"
        assert product.sizes[0].size_value == "M"
        assert product.telegram_posted_at == now

    @patch.dict(os.environ, {"PRICE_MULTIPLIER": "1.5"})
    def test_product_sell_price_with_multiplier(self):
        """Test Product sell_price computation with multiplier."""
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            created_at=datetime.now(),
            price=20.00,
            images=[],
            sizes=[]
        )
        
        assert product.sell_price == 30.0  # 20.00 * 1.5

    @patch.dict(os.environ, {"PRICE_MULTIPLIER": "2.0"})
    def test_product_sell_price_rounding(self):
        """Test Product sell_price rounding."""
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            created_at=datetime.now(),
            price=10.33,
            images=[],
            sizes=[]
        )
        
        assert product.sell_price == 20.66  # 10.33 * 2.0, properly rounded

    def test_product_sell_price_no_price(self):
        """Test Product sell_price when price is None."""
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            created_at=datetime.now(),
            price=None,
            images=[],
            sizes=[]
        )
        
        assert product.sell_price is None

    @patch.dict(os.environ, {}, clear=True)
    def test_product_sell_price_default_multiplier(self):
        """Test Product sell_price with default multiplier."""
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            created_at=datetime.now(),
            price=15.0,
            images=[],
            sizes=[]
        )
        
        assert product.sell_price == 15.0  # Default multiplier is 1.0

    @patch.dict(os.environ, {"PRICE_MULTIPLIER": "invalid"})
    def test_product_sell_price_invalid_multiplier(self):
        """Test Product sell_price with invalid multiplier."""
        product = Product(
            id=1,
            product_url="https://example.com/product/1",
            created_at=datetime.now(),
            price=10.0,
            images=[],
            sizes=[]
        )
        
        assert product.sell_price is None  # Should return None for invalid multiplier

    def test_product_required_fields(self):
        """Test Product required fields."""
        now = datetime.now()
        
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            Product(
                product_url="https://example.com/product",
                created_at=now,
                images=[],
                sizes=[]
            )
        assert "id" in str(exc_info.value)
        
        # Missing created_at
        with pytest.raises(ValidationError) as exc_info:
            Product(
                id=1,
                product_url="https://example.com/product",
                images=[],
                sizes=[]
            )
        assert "created_at" in str(exc_info.value)

    def test_product_serialization(self):
        """Test Product serialization includes computed field."""
        now = datetime.now()
        
        with patch.dict(os.environ, {"PRICE_MULTIPLIER": "1.2"}):
            product = Product(
                id=1,
                product_url="https://example.com/product/1",
                name="Serialization Test",
                price=10.0,
                created_at=now,
                images=[],
                sizes=[]
            )
            
            json_data = product.model_dump()
            
            assert json_data["id"] == 1
            assert json_data["name"] == "Serialization Test"
            assert json_data["price"] == 10.0
            assert json_data["sell_price"] == 12.0  # Computed field
            assert "created_at" in json_data
            assert json_data["images"] == []
            assert json_data["sizes"] == []

    def test_product_inheritance(self):
        """Test that Product inherits from ProductBase."""
        product = Product(
            id=1,
            product_url="https://example.com/product",
            name="Inheritance Test",
            created_at=datetime.now(),
            images=[],
            sizes=[]
        )
        
        assert isinstance(product, ProductBase)


class TestProductSchemaIntegration:
    """Test integration between product schemas."""

    def test_product_with_nested_schemas(self):
        """Test Product containing nested Image and Size schemas."""
        now = datetime.now()
        
        # Create nested schemas
        images = [
            Image(id=1, product_id=1, url="https://example.com/img1.jpg"),
            Image(id=2, product_id=1, url="https://example.com/img2.jpg")
        ]
        
        sizes = [
            Size(id=1, product_id=1, size_type="simple", size_value="S"),
            Size(id=2, product_id=1, size_type="combination", 
                 size1_type="Band", size2_type="Cup",
                 combination_data={"34": ["B"], "36": ["A", "B"]})
        ]
        
        product = Product(
            id=1,
            product_url="https://example.com/complex-product",
            name="Complex Product",
            price=49.99,
            created_at=now,
            images=images,
            sizes=sizes
        )
        
        # Test that nested schemas work correctly
        assert len(product.images) == 2
        assert len(product.sizes) == 2
        assert product.images[0].product_id == 1
        assert product.sizes[1].combination_data == {"34": ["B"], "36": ["A", "B"]}

    def test_product_serialization_with_nested_data(self):
        """Test Product serialization with nested Image and Size data."""
        now = datetime.now()
        
        images = [Image(id=1, product_id=1, url="https://example.com/test.jpg")]
        sizes = [Size(id=1, product_id=1, size_type="simple", size_value="M")]
        
        product = Product(
            id=1,
            product_url="https://example.com/nested-test",
            name="Nested Test",
            created_at=now,
            images=images,
            sizes=sizes
        )
        
        json_data = product.model_dump()
        
        # Check nested data serialization
        assert len(json_data["images"]) == 1
        assert json_data["images"][0]["url"] == "https://example.com/test.jpg"
        assert json_data["images"][0]["product_id"] == 1
        
        assert len(json_data["sizes"]) == 1
        assert json_data["sizes"][0]["size_type"] == "simple"
        assert json_data["sizes"][0]["size_value"] == "M"

    def test_schema_type_conversions(self):
        """Test type conversions across product schemas."""
        # Test that string numbers are converted properly
        product = Product(
            id="1",  # String should convert to int
            product_url="https://example.com/conversion-test",
            price="19.99",  # String should convert to float
            created_at=datetime.now(),
            images=[],
            sizes=[]
        )
        
        assert product.id == 1
        assert product.price == 19.99
        assert isinstance(product.id, int)
        assert isinstance(product.price, float)

    def test_validation_edge_cases(self):
        """Test validation edge cases across schemas."""
        now = datetime.now()
        
        # Test with extreme values
        product = Product(
            id=999999999,
            product_url="https://example.com/edge-case",
            price=0.01,  # Very small price
            created_at=now,
            images=[],
            sizes=[]
        )
        
        assert product.id == 999999999
        assert product.price == 0.01
        
        # Test with very long URL
        long_url = "https://example.com/" + "a" * 1000
        product2 = Product(
            id=1,
            product_url=long_url,
            created_at=now,
            images=[],
            sizes=[]
        )
        
        assert str(product2.product_url) == long_url