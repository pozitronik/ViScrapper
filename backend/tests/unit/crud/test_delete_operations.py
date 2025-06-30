"""
Comprehensive unit tests for delete operations.

This module contains extensive tests for all delete operation functions including
soft_delete_product, hard_delete_product, delete_product_with_mode, restore_product,
get_deleted_products, and permanently_delete_old_soft_deleted.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from pathlib import Path
from sqlalchemy.orm import Session

from crud.delete_operations import (
    soft_delete_product,
    hard_delete_product,
    delete_product_with_mode,
    restore_product,
    get_deleted_products,
    permanently_delete_old_soft_deleted
)
from models.product import Product, Image, Size
from enums.delete_mode import DeleteMode
from exceptions.base import DatabaseException, ProductException


class TestSoftDeleteProduct:
    """Test suite for soft_delete_product function."""

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_success(self, mock_atomic):
        """Test successful product soft deletion."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = None
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        
        # Mock update operations
        mock_db.query.return_value.filter.return_value.update.return_value = 2  # 2 images updated
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = soft_delete_product(mock_db, 123)
        
        assert result is True
        assert mock_product.deleted_at is not None
        mock_db.flush.assert_called_once()

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_not_found(self, mock_atomic):
        """Test soft deletion when product not found."""
        mock_db = Mock(spec=Session)
        
        # Mock product not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ProductException) as exc_info:
            soft_delete_product(mock_db, 999)
        
        assert "Product not found for soft deletion" in str(exc_info.value)
        assert exc_info.value.details["product_id"] == 999

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_already_deleted(self, mock_atomic):
        """Test soft deletion when product already soft deleted."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = datetime.now(timezone.utc)
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = soft_delete_product(mock_db, 123)
            
            assert result is True
            mock_logger.warning.assert_called()
            assert "already soft deleted" in str(mock_logger.warning.call_args)

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_database_exception(self, mock_atomic):
        """Test soft deletion with database exception."""
        mock_db = Mock(spec=Session)
        
        # Mock atomic transaction to raise exception
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            soft_delete_product(mock_db, 123)
        
        assert "Failed to soft delete product" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "soft_delete_product"
        assert exc_info.value.details["product_id"] == 123

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_updates_related_data(self, mock_atomic):
        """Test that soft deletion updates related images and sizes."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = None
        
        # Mock product query
        mock_product_query = Mock()
        mock_product_query.filter.return_value.first.return_value = mock_product
        
        # Mock image query
        mock_image_query = Mock()
        mock_image_query.filter.return_value.filter.return_value.update.return_value = 3
        
        # Mock size query  
        mock_size_query = Mock()
        mock_size_query.filter.return_value.filter.return_value.update.return_value = 2
        
        # Configure query to return different mocks for different model types
        query_calls = []
        def query_side_effect(model):
            query_calls.append(model)
            if model == Product:
                return mock_product_query
            elif model == Image:
                return mock_image_query
            elif model == Size:
                return mock_size_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = soft_delete_product(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log about images and sizes updated
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            success_log = [call for call in log_calls if "Successfully soft deleted" in call]
            assert len(success_log) > 0
            assert "3" in success_log[0]  # 3 images
            assert "2" in success_log[0]  # 2 sizes

    @patch('crud.delete_operations.atomic_transaction')
    def test_soft_delete_product_logging(self, mock_atomic):
        """Test logging behavior in soft_delete_product."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.update.return_value = 0
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = soft_delete_product(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log both start and success messages
            assert mock_logger.info.call_count == 2


class TestHardDeleteProduct:
    """Test suite for hard_delete_product function."""

    @patch('crud.delete_operations.atomic_transaction')
    @patch('crud.delete_operations.IMAGE_DIR', './test_images')
    def test_hard_delete_product_success(self, mock_atomic):
        """Test successful product hard deletion."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        # Mock image with local file
        mock_image = Mock(spec=Image)
        mock_image.url = "test_image.jpg"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_image]
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.unlink') as mock_unlink:
                result = hard_delete_product(mock_db, 123)
                
                assert result is True
                mock_db.delete.assert_called_once_with(mock_product)
                mock_unlink.assert_called_once()

    @patch('crud.delete_operations.atomic_transaction')
    def test_hard_delete_product_not_found(self, mock_atomic):
        """Test hard deletion when product not found."""
        mock_db = Mock(spec=Session)
        
        # Mock product not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ProductException) as exc_info:
            hard_delete_product(mock_db, 999)
        
        assert "Product not found for hard deletion" in str(exc_info.value)
        assert exc_info.value.details["product_id"] == 999

    @patch('crud.delete_operations.atomic_transaction')
    @patch('crud.delete_operations.IMAGE_DIR', './test_images')
    def test_hard_delete_product_with_external_images(self, mock_atomic):
        """Test hard deletion with external image URLs."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        # Mock image with external URL
        mock_image = Mock(spec=Image)
        mock_image.url = "http://example.com/image.jpg"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_image]
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = hard_delete_product(mock_db, 123)
            
            assert result is True
            mock_logger.debug.assert_called()
            # Should log about skipping external URL
            assert any("Skipping external image URL" in str(call) for call in mock_logger.debug.call_args_list)

    @patch('crud.delete_operations.atomic_transaction')
    @patch('crud.delete_operations.IMAGE_DIR', './test_images')
    def test_hard_delete_product_file_not_found(self, mock_atomic):
        """Test hard deletion when image file doesn't exist."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        # Mock image with local file that doesn't exist
        mock_image = Mock(spec=Image)
        mock_image.url = "nonexistent.jpg"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_image]
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('crud.delete_operations.logger') as mock_logger:
                result = hard_delete_product(mock_db, 123)
                
                assert result is True
                mock_logger.debug.assert_called()
                # Should log about file not found
                assert any("Image file not found" in str(call) for call in mock_logger.debug.call_args_list)

    @patch('crud.delete_operations.atomic_transaction')
    @patch('crud.delete_operations.IMAGE_DIR', './test_images')
    def test_hard_delete_product_file_deletion_error(self, mock_atomic):
        """Test hard deletion when file deletion fails."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        # Mock image with local file
        mock_image = Mock(spec=Image)
        mock_image.url = "error_image.jpg"
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_image]
        mock_db.query.return_value.filter.return_value.delete.return_value = 1
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.unlink', side_effect=OSError("Permission denied")):
                with patch('crud.delete_operations.logger') as mock_logger:
                    result = hard_delete_product(mock_db, 123)
                    
                    assert result is True
                    mock_logger.warning.assert_called()
                    # Should log warning about file deletion failure
                    assert "Failed to delete image file" in str(mock_logger.warning.call_args)

    @patch('crud.delete_operations.atomic_transaction')
    def test_hard_delete_product_database_exception(self, mock_atomic):
        """Test hard deletion with database exception."""
        mock_db = Mock(spec=Session)
        
        # Mock atomic transaction to raise exception
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            hard_delete_product(mock_db, 123)
        
        assert "Failed to hard delete product" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "hard_delete_product"
        assert exc_info.value.details["product_id"] == 123

    @patch('crud.delete_operations.atomic_transaction')
    def test_hard_delete_product_logging(self, mock_atomic):
        """Test logging behavior in hard_delete_product."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.delete.return_value = 0
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = hard_delete_product(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log both start and success messages
            assert mock_logger.info.call_count == 2


class TestDeleteProductWithMode:
    """Test suite for delete_product_with_mode function."""

    @patch('crud.delete_operations.soft_delete_product')
    def test_delete_product_with_mode_soft(self, mock_soft_delete):
        """Test delete with soft mode."""
        mock_db = Mock(spec=Session)
        mock_soft_delete.return_value = True
        
        result = delete_product_with_mode(mock_db, 123, DeleteMode.SOFT)
        
        assert result is True
        mock_soft_delete.assert_called_once_with(mock_db, 123)

    @patch('crud.delete_operations.hard_delete_product')
    def test_delete_product_with_mode_hard(self, mock_hard_delete):
        """Test delete with hard mode."""
        mock_db = Mock(spec=Session)
        mock_hard_delete.return_value = True
        
        result = delete_product_with_mode(mock_db, 123, DeleteMode.HARD)
        
        assert result is True
        mock_hard_delete.assert_called_once_with(mock_db, 123)

    def test_delete_product_with_mode_invalid(self):
        """Test delete with invalid mode."""
        mock_db = Mock(spec=Session)
        
        with pytest.raises(ValueError) as exc_info:
            delete_product_with_mode(mock_db, 123, "INVALID_MODE")
        
        assert "Invalid delete mode" in str(exc_info.value)

    @patch('crud.delete_operations.soft_delete_product')
    def test_delete_product_with_mode_logging(self, mock_soft_delete):
        """Test logging behavior in delete_product_with_mode."""
        mock_db = Mock(spec=Session)
        mock_soft_delete.return_value = True
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = delete_product_with_mode(mock_db, 123, DeleteMode.SOFT)
            
            assert result is True
            mock_logger.info.assert_called()
            log_message = str(mock_logger.info.call_args)
            assert "Deleting product 123" in log_message
            assert "soft" in log_message


class TestRestoreProduct:
    """Test suite for restore_product function."""

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_success(self, mock_atomic):
        """Test successful product restoration."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = datetime.now(timezone.utc)
        
        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        
        # Mock update operations for images and sizes
        mock_db.query.return_value.filter.return_value.filter.return_value.update.return_value = 2
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = restore_product(mock_db, 123)
        
        assert result is True
        assert mock_product.deleted_at is None
        mock_db.flush.assert_called_once()

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_not_found(self, mock_atomic):
        """Test restoration when product not found."""
        mock_db = Mock(spec=Session)
        
        # Mock product not found (both soft-deleted and regular queries)
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ProductException) as exc_info:
            restore_product(mock_db, 999)
        
        assert "Product not found for restoration" in str(exc_info.value)
        assert exc_info.value.details["product_id"] == 999

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_not_soft_deleted(self, mock_atomic):
        """Test restoration when product is not soft deleted."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        # Create separate mock queries
        mock_soft_deleted_query = Mock()
        mock_soft_deleted_query.filter.return_value.first.return_value = None
        
        mock_regular_query = Mock()
        mock_regular_query.filter.return_value.first.return_value = mock_product
        
        # Configure query calls to return different mocks
        call_count = 0
        def query_side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call - soft deleted query
                return mock_soft_deleted_query
            else:  # Second call - regular query
                return mock_regular_query
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ProductException) as exc_info:
            restore_product(mock_db, 123)
        
        assert "Product is not soft deleted and cannot be restored" in str(exc_info.value)
        assert exc_info.value.details["product_id"] == 123

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_database_exception(self, mock_atomic):
        """Test restoration with database exception."""
        mock_db = Mock(spec=Session)
        
        # Mock atomic transaction to raise exception
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            restore_product(mock_db, 123)
        
        assert "Failed to restore product" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "restore_product"
        assert exc_info.value.details["product_id"] == 123

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_restores_related_data(self, mock_atomic):
        """Test that restoration updates related images and sizes."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = datetime.now(timezone.utc)
        
        # Mock product query
        mock_product_query = Mock()
        mock_product_query.filter.return_value.first.return_value = mock_product
        
        # Mock image and size queries
        mock_image_query = Mock()
        mock_size_query = Mock()
        mock_image_query.filter.return_value.filter.return_value.update.return_value = 3
        mock_size_query.filter.return_value.filter.return_value.update.return_value = 2
        
        # Configure query to return different mocks for different calls
        query_call_count = 0
        def query_side_effect(*args):
            nonlocal query_call_count
            query_call_count += 1
            if query_call_count == 1:  # First call for finding product
                return mock_product_query
            elif query_call_count == 2:  # Images update
                return mock_image_query
            elif query_call_count == 3:  # Sizes update
                return mock_size_query
            return Mock()
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = restore_product(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log about images and sizes restored
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            success_log = [call for call in log_calls if "Successfully restored" in call]
            assert len(success_log) > 0
            assert "3" in success_log[0]  # 3 images
            assert "2" in success_log[0]  # 2 sizes

    @patch('crud.delete_operations.atomic_transaction')
    def test_restore_product_logging(self, mock_atomic):
        """Test logging behavior in restore_product."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.deleted_at = datetime.now(timezone.utc)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_product
        mock_db.query.return_value.filter.return_value.filter.return_value.update.return_value = 0
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = restore_product(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log both start and success messages
            assert mock_logger.info.call_count == 2


class TestGetDeletedProducts:
    """Test suite for get_deleted_products function."""

    def test_get_deleted_products_success(self):
        """Test successful retrieval of deleted products."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product), Mock(spec=Product)]
        
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        result = get_deleted_products(mock_db, skip=10, limit=20)
        
        assert result == mock_products
        mock_db.query.assert_called_once_with(Product)

    def test_get_deleted_products_empty_result(self):
        """Test retrieval when no deleted products exist."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        result = get_deleted_products(mock_db)
        
        assert result == []

    def test_get_deleted_products_database_exception(self):
        """Test retrieval with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_deleted_products(mock_db)
        
        assert "Failed to retrieve deleted products list" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_deleted_products"

    def test_get_deleted_products_logging(self):
        """Test logging behavior in get_deleted_products."""
        mock_db = Mock(spec=Session)
        mock_products = [Mock(spec=Product)]
        
        mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_products
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = get_deleted_products(mock_db, skip=5, limit=10)
            
            assert result == mock_products
            mock_logger.debug.assert_called()
            # Should log both fetch and result messages
            assert mock_logger.debug.call_count == 2


class TestPermanentlyDeleteOldSoftDeleted:
    """Test suite for permanently_delete_old_soft_deleted function."""

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_success(self, mock_hard_delete):
        """Test successful permanent deletion of old soft-deleted products."""
        mock_db = Mock(spec=Session)
        
        # Mock old soft-deleted products
        mock_product1 = Mock(spec=Product)
        mock_product1.id = 1
        mock_product2 = Mock(spec=Product)
        mock_product2.id = 2
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_product1, mock_product2]
        mock_hard_delete.return_value = True
        
        result = permanently_delete_old_soft_deleted(mock_db, days_old=30)
        
        assert result == 2
        assert mock_hard_delete.call_count == 2
        mock_hard_delete.assert_any_call(mock_db, 1)
        mock_hard_delete.assert_any_call(mock_db, 2)

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_empty_result(self, mock_hard_delete):
        """Test permanent deletion when no old products exist."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = permanently_delete_old_soft_deleted(mock_db, days_old=30)
        
        assert result == 0
        mock_hard_delete.assert_not_called()

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_partial_failure(self, mock_hard_delete):
        """Test permanent deletion with some failures."""
        mock_db = Mock(spec=Session)
        
        # Mock old soft-deleted products
        mock_product1 = Mock(spec=Product)
        mock_product1.id = 1
        mock_product2 = Mock(spec=Product)
        mock_product2.id = 2
        mock_product3 = Mock(spec=Product)
        mock_product3.id = 3
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_product1, mock_product2, mock_product3]
        
        # Mock hard delete to fail for second product
        def hard_delete_side_effect(db, product_id):
            if product_id == 2:
                raise Exception("Delete failed")
            return True
        
        mock_hard_delete.side_effect = hard_delete_side_effect
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = permanently_delete_old_soft_deleted(mock_db, days_old=30)
            
            assert result == 2  # Only 2 succeeded
            assert mock_hard_delete.call_count == 3
            mock_logger.error.assert_called()
            assert "Failed to permanently delete product 2" in str(mock_logger.error.call_args)

    def test_permanently_delete_old_soft_deleted_database_exception(self):
        """Test permanent deletion with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            permanently_delete_old_soft_deleted(mock_db, days_old=30)
        
        assert "Failed to permanently delete old soft-deleted products" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "permanently_delete_old_soft_deleted"
        assert exc_info.value.details["days_old"] == 30

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_cutoff_calculation(self, mock_hard_delete):
        """Test that cutoff date is calculated correctly."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_product]
        mock_hard_delete.return_value = True
        
        # Mock datetime to control the "now" time
        mock_now = datetime(2023, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        with patch('crud.delete_operations.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw) if args else mock_now
            
            # Also need to patch timedelta import
            with patch('crud.delete_operations.timedelta') as mock_timedelta:
                mock_timedelta.side_effect = timedelta
                
                result = permanently_delete_old_soft_deleted(mock_db, days_old=7)
                
                # Verify the function was called and returned successfully
                assert result == 1
                mock_hard_delete.assert_called_once_with(mock_db, 1)
                
                # Verify datetime.now was called to calculate cutoff
                mock_datetime.now.assert_called_once_with(timezone.utc)

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_logging(self, mock_hard_delete):
        """Test logging behavior in permanently_delete_old_soft_deleted."""
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_product]
        mock_hard_delete.return_value = True
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = permanently_delete_old_soft_deleted(mock_db, days_old=30)
            
            assert result == 1
            mock_logger.info.assert_called()
            # Should log both start and completion messages
            assert mock_logger.info.call_count == 2
            assert "Permanently deleting products soft-deleted more than 30 days ago" in str(mock_logger.info.call_args_list[0])
            assert "Permanently deleted 1 old soft-deleted products" in str(mock_logger.info.call_args_list[1])

    @patch('crud.delete_operations.hard_delete_product')
    def test_permanently_delete_old_soft_deleted_custom_days(self, mock_hard_delete):
        """Test permanent deletion with custom days parameter."""
        mock_db = Mock(spec=Session)
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with patch('crud.delete_operations.logger') as mock_logger:
            result = permanently_delete_old_soft_deleted(mock_db, days_old=60)
            
            assert result == 0
            mock_logger.info.assert_called()
            assert "60 days ago" in str(mock_logger.info.call_args_list[0])