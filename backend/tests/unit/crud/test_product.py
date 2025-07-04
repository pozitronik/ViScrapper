"""
Comprehensive unit tests for product CRUD operations.

This module contains extensive tests for all product CRUD functions including
get_product_by_url, get_product_by_sku, find_existing_product, compare_product_data,
create_product, update_existing_product_with_changes, get_product_by_id,
get_products, update_product, delete_product, and get_product_count.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from crud.product import (
    get_product_by_url,
    get_product_by_sku,
    find_existing_product,
    compare_product_data,
    create_product,
    update_existing_product_with_changes,
    get_product_by_id,
    get_products,
    update_product,
    delete_product,
    get_product_count,
    create_size_combinations_new,
    create_simple_sizes,
    filter_duplicate_images_by_hash,
    delete_product_image
)
from models.product import Product, Image, Size
from schemas.product import ProductCreate, ProductUpdate
from exceptions.base import DatabaseException, ValidationException, ProductException


class TestGetProductByUrl:
    """Test suite for get_product_by_url function."""

    def test_get_product_by_url_found(self):
        """Test successful product retrieval by URL."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        result = get_product_by_url(mock_db, "http://example.com/product")
        
        assert result == mock_product
        mock_db.query.assert_called_once_with(Product)
        mock_query.filter.assert_called_once()
        mock_filter.filter.assert_called_once()

    def test_get_product_by_url_not_found(self):
        """Test product retrieval when URL not found."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = get_product_by_url(mock_db, "http://example.com/nonexistent")
        
        assert result is None

    def test_get_product_by_url_include_deleted(self):
        """Test product retrieval with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        result = get_product_by_url(mock_db, "http://example.com/product", include_deleted=True)
        
        assert result == mock_product
        # Should not call filter twice when include_deleted=True
        mock_query.filter.assert_called_once()
        mock_filter.filter.assert_not_called()

    def test_get_product_by_url_logging(self):
        """Test logging behavior in get_product_by_url."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        mock_product.id = 123
        
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        with patch('crud.product.logger') as mock_logger:
            result = get_product_by_url(mock_db, "http://example.com/product")
            
            assert result == mock_product
            mock_logger.debug.assert_called()
            # Should log both search and found messages
            assert mock_logger.debug.call_count == 2


class TestGetProductBySku:
    """Test suite for get_product_by_sku function."""

    def test_get_product_by_sku_found(self):
        """Test successful product retrieval by SKU."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        result = get_product_by_sku(mock_db, "SKU123")
        
        assert result == mock_product
        mock_db.query.assert_called_once_with(Product)
        mock_query.options.assert_called_once()
        mock_query.filter.assert_called_once()

    def test_get_product_by_sku_not_found(self):
        """Test product retrieval when SKU not found."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = get_product_by_sku(mock_db, "NONEXISTENT")
        
        assert result is None

    def test_get_product_by_sku_include_deleted(self):
        """Test product retrieval by SKU with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        result = get_product_by_sku(mock_db, "SKU123", include_deleted=True)
        
        assert result == mock_product
        # Should not call filter twice when include_deleted=True
        mock_query.filter.assert_called_once()
        mock_filter.filter.assert_not_called()

    def test_get_product_by_sku_with_relationships(self):
        """Test that get_product_by_sku loads relationships."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_product = Mock(spec=Product)
        
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_product
        
        result = get_product_by_sku(mock_db, "SKU123")
        
        assert result == mock_product
        # Verify relationships are loaded
        mock_query.options.assert_called_once()


class TestFindExistingProduct:
    """Test suite for find_existing_product function."""

    @patch('crud.product.get_product_by_url')
    @patch('crud.product.get_product_by_sku')
    def test_find_existing_product_by_url(self, mock_get_by_sku, mock_get_by_url):
        """Test finding existing product by URL match."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_get_by_url.return_value = mock_product
        mock_get_by_sku.return_value = None
        
        result = find_existing_product(mock_db, "http://example.com/product", "SKU123")
        
        assert result['product'] == mock_product
        assert result['match_type'] == 'url'
        mock_get_by_url.assert_called_once_with(mock_db, "http://example.com/product", False)
        mock_get_by_sku.assert_not_called()

    @patch('crud.product.get_product_by_url')
    @patch('crud.product.get_product_by_sku')
    def test_find_existing_product_by_sku(self, mock_get_by_sku, mock_get_by_url):
        """Test finding existing product by SKU match."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_get_by_url.return_value = None
        mock_get_by_sku.return_value = mock_product
        
        result = find_existing_product(mock_db, "http://example.com/product", "SKU123")
        
        assert result['product'] == mock_product
        assert result['match_type'] == 'sku'
        mock_get_by_url.assert_called_once_with(mock_db, "http://example.com/product", False)
        mock_get_by_sku.assert_called_once_with(mock_db, "SKU123", False)

    @patch('crud.product.get_product_by_url')
    @patch('crud.product.get_product_by_sku')
    def test_find_existing_product_not_found(self, mock_get_by_sku, mock_get_by_url):
        """Test finding existing product when none exists."""
        mock_db = Mock(spec=Session)
        mock_get_by_url.return_value = None
        mock_get_by_sku.return_value = None
        
        result = find_existing_product(mock_db, "http://example.com/product", "SKU123")
        
        assert result['product'] is None
        assert result['match_type'] is None
        mock_get_by_url.assert_called_once()
        mock_get_by_sku.assert_called_once()

    @patch('crud.product.get_product_by_url')
    @patch('crud.product.get_product_by_sku')
    def test_find_existing_product_no_sku(self, mock_get_by_sku, mock_get_by_url):
        """Test finding existing product when no SKU provided."""
        mock_db = Mock(spec=Session)
        mock_get_by_url.return_value = None
        
        result = find_existing_product(mock_db, "http://example.com/product")
        
        assert result['product'] is None
        assert result['match_type'] is None
        mock_get_by_url.assert_called_once()
        mock_get_by_sku.assert_not_called()

    @patch('crud.product.get_product_by_url')
    @patch('crud.product.get_product_by_sku')
    def test_find_existing_product_include_deleted(self, mock_get_by_sku, mock_get_by_url):
        """Test finding existing product with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_get_by_url.return_value = mock_product
        
        result = find_existing_product(mock_db, "http://example.com/product", "SKU123", include_deleted=True)
        
        assert result['product'] == mock_product
        assert result['match_type'] == 'url'
        mock_get_by_url.assert_called_once_with(mock_db, "http://example.com/product", True)


class TestCompareProductData:
    """Test suite for compare_product_data function."""

    def test_compare_product_data_no_changes(self):
        """Test comparison when no changes detected."""
        existing_product = Mock(spec=Product)
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "nice"
        existing_product.images = []
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "nice"
        new_data.all_image_urls = []
        new_data.available_sizes = []
        
        result = compare_product_data(existing_product, new_data)
        
        assert result['has_changes'] is False
        assert result['field_changes'] == {}
        assert not result['image_changes']['to_add']
        assert not result['image_changes']['to_remove']
        assert not result['size_changes']['to_add']
        assert not result['size_changes']['to_remove']

    def test_compare_product_data_field_changes(self):
        """Test comparison when basic fields have changed."""
        existing_product = Mock(spec=Product)
        existing_product.name = "Old Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "old comment"
        existing_product.images = []
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "New Product"
        new_data.price = 150.0
        new_data.currency = "EUR"
        new_data.availability = "out_of_stock"
        new_data.color = "blue"
        new_data.composition = "polyester"
        new_data.item = "jacket"
        new_data.comment = "new comment"
        new_data.all_image_urls = []
        new_data.available_sizes = []
        
        result = compare_product_data(existing_product, new_data)
        
        assert result['has_changes'] is True
        assert len(result['field_changes']) == 8
        assert result['field_changes']['name']['old'] == "Old Product"
        assert result['field_changes']['name']['new'] == "New Product"
        assert result['field_changes']['price']['old'] == 100.0
        assert result['field_changes']['price']['new'] == 150.0

    def test_compare_product_data_string_normalization(self):
        """Test string normalization in field comparison."""
        existing_product = Mock(spec=Product)
        existing_product.name = "  Test Product  "
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = []
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = []
        new_data.available_sizes = []
        
        result = compare_product_data(existing_product, new_data)
        
        # Should not detect changes due to string normalization
        assert result['has_changes'] is False
        assert 'name' not in result['field_changes']

    def test_compare_product_data_image_changes(self):
        """Test comparison when images have changed."""
        existing_image1 = Mock(spec=Image)
        existing_image1.url = "http://example.com/image1.jpg"
        existing_image1.file_hash = "hash1"
        existing_image1.deleted_at = None
        
        existing_image2 = Mock(spec=Image)
        existing_image2.url = "http://example.com/image2.jpg"
        existing_image2.file_hash = "hash2"
        existing_image2.deleted_at = None
        
        existing_product = Mock(spec=Product)
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = [existing_image1, existing_image2]
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = ["http://example.com/image2.jpg", "http://example.com/image3.jpg"]
        new_data.available_sizes = []
        
        result = compare_product_data(existing_product, new_data)
        
        assert result['has_changes'] is True
        assert "http://example.com/image3.jpg" in result['image_changes']['to_add']
        assert "http://example.com/image1.jpg" in result['image_changes']['to_remove']
        assert "http://example.com/image2.jpg" in result['image_changes']['existing']

    def test_compare_product_data_size_changes(self):
        """Test comparison when sizes have changed."""
        existing_size1 = Mock(spec=Size)
        existing_size1.size_value = "S"
        existing_size1.deleted_at = None
        
        existing_size2 = Mock(spec=Size)
        existing_size2.size_value = "M"
        existing_size2.deleted_at = None
        
        existing_product = Mock(spec=Product)
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = []
        existing_product.sizes = [existing_size1, existing_size2]
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = []
        new_data.available_sizes = ["M", "L", "XL"]
        
        result = compare_product_data(existing_product, new_data)
        
        assert result['has_changes'] is True
        assert "L" in result['size_changes']['to_add']
        assert "XL" in result['size_changes']['to_add']
        assert "S" in result['size_changes']['to_remove']
        assert "M" in result['size_changes']['existing']

    def test_compare_product_data_ignore_deleted_images(self):
        """Test that deleted images are ignored in comparison."""
        existing_image1 = Mock(spec=Image)
        existing_image1.url = "http://example.com/image1.jpg"
        existing_image1.file_hash = "hash1"
        existing_image1.deleted_at = None
        
        deleted_image = Mock(spec=Image)
        deleted_image.url = "http://example.com/deleted.jpg"
        deleted_image.file_hash = "hash_deleted"
        deleted_image.deleted_at = datetime.now(timezone.utc)
        
        existing_product = Mock(spec=Product)
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = [existing_image1, deleted_image]
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = ["http://example.com/image1.jpg"]
        new_data.available_sizes = []
        
        result = compare_product_data(existing_product, new_data)
        
        # Should not detect changes since deleted image is ignored
        assert result['has_changes'] is False
        assert not result['image_changes']['to_add']
        assert not result['image_changes']['to_remove']
        assert "hash_deleted" not in result['image_changes']['existing_hashes']

    def test_compare_product_data_ignore_deleted_sizes(self):
        """Test that deleted sizes are ignored in comparison."""
        existing_size1 = Mock(spec=Size)
        existing_size1.size_value = "S"
        existing_size1.deleted_at = None
        
        deleted_size = Mock(spec=Size)
        deleted_size.size_value = "DELETED"
        deleted_size.deleted_at = datetime.now(timezone.utc)
        
        existing_product = Mock(spec=Product)
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = []
        existing_product.sizes = [existing_size1, deleted_size]
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = []
        new_data.available_sizes = ["S"]
        
        result = compare_product_data(existing_product, new_data)
        
        # Should not detect changes since deleted size is ignored
        assert result['has_changes'] is False
        assert not result['size_changes']['to_add']
        assert not result['size_changes']['to_remove']

    def test_compare_product_data_logging(self):
        """Test logging behavior in compare_product_data."""
        existing_product = Mock(spec=Product)
        existing_product.id = 123
        existing_product.name = "Test Product"
        existing_product.price = 100.0
        existing_product.currency = "USD"
        existing_product.availability = "in_stock"
        existing_product.color = "red"
        existing_product.composition = "cotton"
        existing_product.item = "shirt"
        existing_product.comment = "comment"
        existing_product.images = []
        existing_product.sizes = []
        
        new_data = Mock(spec=ProductCreate)
        new_data.name = "Test Product"
        new_data.price = 100.0
        new_data.currency = "USD"
        new_data.availability = "in_stock"
        new_data.color = "red"
        new_data.composition = "cotton"
        new_data.item = "shirt"
        new_data.comment = "comment"
        new_data.all_image_urls = []
        new_data.available_sizes = []
        
        with patch('crud.product.logger') as mock_logger:
            result = compare_product_data(existing_product, new_data)
            
            assert result['has_changes'] is False
            mock_logger.debug.assert_called()
            # Should log both start and completion messages
            assert mock_logger.debug.call_count == 2


class TestFilterDuplicateImagesByHash:
    """Test suite for filter_duplicate_images_by_hash function."""

    def test_filter_duplicate_images_by_hash_no_duplicates(self):
        """Test filtering when no duplicates exist."""
        new_images = [
            {"url": "http://example.com/image1.jpg", "file_hash": "hash1"},
            {"url": "http://example.com/image2.jpg", "file_hash": "hash2"},
            {"url": "http://example.com/image3.jpg", "file_hash": "hash3"}
        ]
        existing_hashes = {"hash4", "hash5"}
        
        result = filter_duplicate_images_by_hash(new_images, existing_hashes)
        
        assert len(result) == 3
        assert result == new_images

    def test_filter_duplicate_images_by_hash_with_duplicates(self):
        """Test filtering when duplicates exist."""
        new_images = [
            {"url": "http://example.com/image1.jpg", "file_hash": "hash1"},
            {"url": "http://example.com/image2.jpg", "file_hash": "hash2"},
            {"url": "http://example.com/image3.jpg", "file_hash": "hash3"}
        ]
        existing_hashes = {"hash2", "hash4"}
        
        result = filter_duplicate_images_by_hash(new_images, existing_hashes)
        
        assert len(result) == 2
        assert result[0]["file_hash"] == "hash1"
        assert result[1]["file_hash"] == "hash3"

    def test_filter_duplicate_images_by_hash_no_hash(self):
        """Test filtering when some images have no hash."""
        new_images = [
            {"url": "http://example.com/image1.jpg", "file_hash": "hash1"},
            {"url": "http://example.com/image2.jpg"},  # No hash
            {"url": "http://example.com/image3.jpg", "file_hash": None}  # None hash
        ]
        existing_hashes = {"hash1"}
        
        result = filter_duplicate_images_by_hash(new_images, existing_hashes)
        
        assert len(result) == 2
        # Should include images without hash
        assert any(img.get("url") == "http://example.com/image2.jpg" for img in result)
        assert any(img.get("url") == "http://example.com/image3.jpg" for img in result)

    def test_filter_duplicate_images_by_hash_empty_inputs(self):
        """Test filtering with empty inputs."""
        result = filter_duplicate_images_by_hash([], set())
        assert result == []
        
        result = filter_duplicate_images_by_hash([], {"hash1"})
        assert result == []

    def test_filter_duplicate_images_by_hash_logging(self):
        """Test logging behavior in filter_duplicate_images_by_hash."""
        new_images = [
            {"url": "http://example.com/image1.jpg", "file_hash": "hash1"},
            {"url": "http://example.com/image2.jpg", "file_hash": "hash2"}
        ]
        existing_hashes = {"hash1"}
        
        with patch('crud.product.logger') as mock_logger:
            result = filter_duplicate_images_by_hash(new_images, existing_hashes)
            
            assert len(result) == 1
            mock_logger.debug.assert_called()
            # Should log about skipping duplicate
            assert "Skipping duplicate image" in str(mock_logger.debug.call_args)


class TestCreateSizeCombinationsNew:
    """Test suite for create_size_combinations_new function."""

    def test_create_size_combinations_new_success(self):
        """Test successful size combinations creation."""
        mock_db = Mock(spec=Session)
        product_id = 123
        combinations_data = {
            "size1_type": "chest",
            "size2_type": "length",
            "combinations": {
                "S": {"36": True, "38": True},
                "M": {"38": True, "40": True}
            }
        }
        
        create_size_combinations_new(mock_db, product_id, combinations_data)
        
        mock_db.add.assert_called_once()
        # Verify the Size object was created with correct data
        added_size = mock_db.add.call_args[0][0]
        assert added_size.product_id == product_id
        assert added_size.size_type == "combination"
        assert added_size.size1_type == "chest"
        assert added_size.size2_type == "length"
        assert added_size.combination_data == combinations_data["combinations"]

    def test_create_size_combinations_new_no_combinations(self):
        """Test size combinations creation with no combinations data."""
        mock_db = Mock(spec=Session)
        product_id = 123
        combinations_data = {
            "size1_type": "chest",
            "size2_type": "length",
            "combinations": {}
        }
        
        with patch('crud.product.logger') as mock_logger:
            create_size_combinations_new(mock_db, product_id, combinations_data)
            
            mock_db.add.assert_not_called()
            mock_logger.warning.assert_called()
            assert "No combinations data found" in str(mock_logger.warning.call_args)

    def test_create_size_combinations_new_defaults(self):
        """Test size combinations creation with default values."""
        mock_db = Mock(spec=Session)
        product_id = 123
        combinations_data = {
            "combinations": {
                "S": {"36": True}
            }
        }
        
        create_size_combinations_new(mock_db, product_id, combinations_data)
        
        mock_db.add.assert_called_once()
        added_size = mock_db.add.call_args[0][0]
        assert added_size.size1_type == "size1"  # Default value
        assert added_size.size2_type == "size2"  # Default value

    def test_create_size_combinations_new_logging(self):
        """Test logging behavior in create_size_combinations_new."""
        mock_db = Mock(spec=Session)
        product_id = 123
        combinations_data = {
            "combinations": {
                "S": {"36": True},
                "M": {"38": True}
            }
        }
        
        with patch('crud.product.logger') as mock_logger:
            create_size_combinations_new(mock_db, product_id, combinations_data)
            
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()
            assert "Creating size combinations" in str(mock_logger.debug.call_args)
            assert "Created size combination record" in str(mock_logger.info.call_args)


class TestCreateSimpleSizes:
    """Test suite for create_simple_sizes function."""

    def test_create_simple_sizes_success(self):
        """Test successful simple sizes creation."""
        mock_db = Mock(spec=Session)
        product_id = 123
        available_sizes = ["S", "M", "L", "XL"]
        
        create_simple_sizes(mock_db, product_id, available_sizes)
        
        assert mock_db.add.call_count == 4
        # Verify each size was created correctly
        for i, size_value in enumerate(available_sizes):
            added_size = mock_db.add.call_args_list[i][0][0]
            assert added_size.product_id == product_id
            assert added_size.size_type == "simple"
            assert added_size.size_value == size_value

    def test_create_simple_sizes_empty_list(self):
        """Test simple sizes creation with empty list."""
        mock_db = Mock(spec=Session)
        product_id = 123
        available_sizes = []
        
        with patch('crud.product.logger') as mock_logger:
            create_simple_sizes(mock_db, product_id, available_sizes)
            
            mock_db.add.assert_not_called()
            mock_logger.warning.assert_called()
            assert "No available sizes found" in str(mock_logger.warning.call_args)

    def test_create_simple_sizes_logging(self):
        """Test logging behavior in create_simple_sizes."""
        mock_db = Mock(spec=Session)
        product_id = 123
        available_sizes = ["S", "M"]
        
        with patch('crud.product.logger') as mock_logger:
            create_simple_sizes(mock_db, product_id, available_sizes)
            
            mock_logger.debug.assert_called()
            mock_logger.info.assert_called()
            assert "Creating simple sizes" in str(mock_logger.debug.call_args)
            assert "Created 2 simple size records" in str(mock_logger.info.call_args)


class TestGetProductById:
    """Test suite for get_product_by_id function."""

    def test_get_product_by_id_found(self):
        """Test successful product retrieval by ID."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        
        mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.first.return_value = mock_product
        
        result = get_product_by_id(mock_db, 123)
        
        assert result == mock_product
        mock_db.query.assert_called_once_with(Product)

    def test_get_product_by_id_not_found(self):
        """Test product retrieval by ID when not found."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        result = get_product_by_id(mock_db, 999)
        
        assert result is None

    def test_get_product_by_id_include_deleted(self):
        """Test product retrieval by ID with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_product
        
        result = get_product_by_id(mock_db, 123, include_deleted=True)
        
        assert result == mock_product
        # Should not call filter twice when include_deleted=True
        query_mock = mock_db.query.return_value.options.return_value.filter.return_value
        query_mock.filter.assert_not_called()

    def test_get_product_by_id_database_exception(self):
        """Test product retrieval by ID with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_product_by_id(mock_db, 123)
        
        assert "Failed to retrieve product by ID" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_product_by_id"
        assert exc_info.value.details["product_id"] == 123

    def test_get_product_by_id_logging(self):
        """Test logging behavior in get_product_by_id."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        
        mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.first.return_value = mock_product
        
        with patch('crud.product.logger') as mock_logger:
            result = get_product_by_id(mock_db, 123)
            
            assert result == mock_product
            mock_logger.debug.assert_called()
            # Should log both search and found messages
            assert mock_logger.debug.call_count == 2


class TestGetProducts:
    """Test suite for get_products function."""

    def test_get_products_success(self):
        """Test successful products retrieval."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product), Mock(spec=Product)]
        
        mock_db.query.return_value.filter.return_value.options.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        result = get_products(mock_db, skip=10, limit=20)
        
        assert result == mock_products
        mock_db.query.assert_called_once_with(Product)

    def test_get_products_include_deleted(self):
        """Test products retrieval with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product)]
        
        mock_db.query.return_value.options.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        result = get_products(mock_db, include_deleted=True)
        
        assert result == mock_products
        # Should not call filter when include_deleted=True
        mock_db.query.return_value.filter.assert_not_called()

    def test_get_products_no_relationships(self):
        """Test products retrieval without loading relationships."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product)]
        
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        result = get_products(mock_db, load_relationships=False)
        
        assert result == mock_products
        # Should not call options when load_relationships=False
        mock_db.query.return_value.filter.return_value.options.assert_not_called()

    def test_get_products_database_exception(self):
        """Test products retrieval with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_products(mock_db)
        
        assert "Failed to retrieve products list" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_products"

    def test_get_products_logging(self):
        """Test logging behavior in get_products."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product), Mock(spec=Product)]
        
        mock_db.query.return_value.filter.return_value.options.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        with patch('crud.product.logger') as mock_logger:
            result = get_products(mock_db, skip=5, limit=10)
            
            assert result == mock_products
            mock_logger.debug.assert_called()
            # Should log both fetch and result messages
            assert mock_logger.debug.call_count == 2


class TestGetProductCount:
    """Test suite for get_product_count function."""

    def test_get_product_count_success(self):
        """Test successful product count retrieval."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.count.return_value = 42
        
        result = get_product_count(mock_db)
        
        assert result == 42
        mock_db.query.assert_called_once_with(Product)

    def test_get_product_count_include_deleted(self):
        """Test product count with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.count.return_value = 100
        
        result = get_product_count(mock_db, include_deleted=True)
        
        assert result == 100
        # Should not call filter when include_deleted=True
        mock_db.query.return_value.filter.assert_not_called()

    def test_get_product_count_database_exception(self):
        """Test product count with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_product_count(mock_db)
        
        assert "Failed to get product count" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_product_count"

    def test_get_product_count_logging(self):
        """Test logging behavior in get_product_count."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.count.return_value = 25
        
        with patch('crud.product.logger') as mock_logger:
            result = get_product_count(mock_db)
            
            assert result == 25
            mock_logger.debug.assert_called()
            assert "Total product count: 25" in str(mock_logger.debug.call_args)


class TestDeleteProduct:
    """Test suite for delete_product function."""

    @patch('crud.delete_operations.soft_delete_product')
    def test_delete_product_success(self, mock_soft_delete):
        """Test successful product deletion."""
        mock_db = Mock(spec=Session)
        mock_soft_delete.return_value = True
        
        result = delete_product(mock_db, 123)
        
        assert result is True
        mock_soft_delete.assert_called_once_with(mock_db, 123)

    @patch('crud.delete_operations.soft_delete_product')
    def test_delete_product_failure(self, mock_soft_delete):
        """Test product deletion failure."""
        mock_db = Mock(spec=Session)
        mock_soft_delete.return_value = False
        
        result = delete_product(mock_db, 123)
        
        assert result is False
        mock_soft_delete.assert_called_once_with(mock_db, 123)

    @patch('crud.delete_operations.soft_delete_product')
    def test_delete_product_exception(self, mock_soft_delete):
        """Test product deletion with exception."""
        mock_db = Mock(spec=Session)
        mock_soft_delete.side_effect = ProductException("Product not found")
        
        with pytest.raises(ProductException):
            delete_product(mock_db, 123)
        
        mock_soft_delete.assert_called_once_with(mock_db, 123)


class TestDeleteProductImage:
    """Test suite for delete_product_image function."""

    @patch('os.path.exists')
    @patch('os.remove')
    @patch.dict('os.environ', {'IMAGE_DIR': './test_images'})
    def test_delete_product_image_success(self, mock_remove, mock_exists):
        """Test successful deletion of product image."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_image = Mock(spec=Image)
        mock_image.id = 1
        mock_image.product_id = 123
        mock_image.url = "/static/images/test_image.jpg"
        
        # Setup query chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_image
        mock_exists.return_value = True
        
        # Mock func.now()
        with patch('sqlalchemy.func.now') as mock_now:
            mock_now.return_value = datetime.now()
            
            result = delete_product_image(mock_db, 123, 1)
        
        assert result == mock_image
        assert mock_image.deleted_at is not None
        mock_db.commit.assert_called_once()
        assert mock_exists.call_args_list[-1] == call('./test_images/test_image.jpg')
        mock_remove.assert_called_once_with('./test_images/test_image.jpg')

    def test_delete_product_image_not_found(self):
        """Test deletion of non-existent image."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        
        # Setup query chain to return None
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = delete_product_image(mock_db, 123, 999)
        
        assert result is None
        mock_db.commit.assert_not_called()

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_product_image_file_not_found(self, mock_remove, mock_exists):
        """Test deletion when image file doesn't exist on disk."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_image = Mock(spec=Image)
        mock_image.id = 1
        mock_image.product_id = 123
        mock_image.url = "/static/images/missing_image.jpg"
        
        # Setup query chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_image
        mock_exists.return_value = False  # File doesn't exist
        
        with patch('sqlalchemy.func.now') as mock_now:
            mock_now.return_value = datetime.now()
            
            result = delete_product_image(mock_db, 123, 1)
        
        assert result == mock_image
        assert mock_image.deleted_at is not None
        mock_db.commit.assert_called_once()
        # Check that exists was called for our file specifically
        assert any('./images/missing_image.jpg' in str(call_args) for call_args in mock_exists.call_args_list)
        mock_remove.assert_not_called()  # Should not try to remove non-existent file

    @patch('os.path.exists')
    def test_delete_product_image_no_url(self, mock_exists):
        """Test deletion when image has no URL."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_image = Mock(spec=Image)
        mock_image.id = 1
        mock_image.product_id = 123
        mock_image.url = None  # No URL
        
        # Setup query chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_image
        
        with patch('sqlalchemy.func.now') as mock_now:
            mock_now.return_value = datetime.now()
            
            result = delete_product_image(mock_db, 123, 1)
        
        assert result == mock_image
        assert mock_image.deleted_at is not None
        mock_db.commit.assert_called_once()
        mock_exists.assert_not_called()  # Should not check file existence

    def test_delete_product_image_wrong_product(self):
        """Test deletion when image belongs to different product."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        
        # Setup query chain to return None (no match for product_id + image_id)
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        
        result = delete_product_image(mock_db, 123, 1)  # Image 1 doesn't belong to product 123
        
        assert result is None
        mock_db.commit.assert_not_called()

    def test_delete_product_image_database_exception(self):
        """Test deletion with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            delete_product_image(mock_db, 123, 1)
        
        assert "Failed to delete image 1 from product 123" in str(exc_info.value)
        mock_db.rollback.assert_called_once()

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_product_image_file_removal_error(self, mock_remove, mock_exists):
        """Test deletion when file removal fails."""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_filter = Mock()
        mock_image = Mock(spec=Image)
        mock_image.id = 1
        mock_image.product_id = 123
        mock_image.url = "/static/images/test_image.jpg"
        
        # Setup query chain
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_image
        mock_exists.return_value = True
        mock_remove.side_effect = OSError("Permission denied")  # File removal fails
        
        with patch('sqlalchemy.func.now') as mock_now:
            mock_now.return_value = datetime.now()
            
            # Should still succeed even if file removal fails
            with pytest.raises(DatabaseException):
                delete_product_image(mock_db, 123, 1)