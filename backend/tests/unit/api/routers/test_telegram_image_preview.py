"""
Tests for Telegram image preview endpoint
"""
import pytest
import os
import uuid
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.product import Product, Image as ProductImage, MessageTemplate
from schemas.template import MessageTemplateCreate


class TestTelegramImagePreview:
    """Test suite for Telegram image preview endpoint."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_product(self):
        """Create sample product with images."""
        product = Mock(spec=Product)
        product.id = 1
        product.name = "Test Product"
        
        # Create sample images
        image1 = Mock(spec=ProductImage)
        image1.id = 1
        image1.url = "test_image_1.jpg"
        image1.deleted_at = None
        
        image2 = Mock(spec=ProductImage)
        image2.id = 2
        image2.url = "test_image_2.jpg"
        image2.deleted_at = None
        
        product.images = [image1, image2]
        return product
    
    @pytest.fixture
    def sample_template_combine(self):
        """Create sample template with image combination enabled."""
        template = Mock(spec=MessageTemplate)
        template.id = 1
        template.name = "Combine Template"
        template.combine_images = True
        template.optimize_images = False
        template.max_width = 1920
        template.max_height = 1080
        template.max_file_size_kb = 500
        template.compression_quality = 80
        return template
    
    @pytest.fixture
    def sample_template_optimize(self):
        """Create sample template with optimization only."""
        template = Mock(spec=MessageTemplate)
        template.id = 2
        template.name = "Optimize Template"
        template.combine_images = False
        template.optimize_images = True
        template.max_width = 1200
        template.max_height = 800
        template.max_file_size_kb = 300
        template.compression_quality = 70
        return template
    
    @pytest.fixture
    def sample_template_both(self):
        """Create sample template with both combination and optimization."""
        template = Mock(spec=MessageTemplate)
        template.id = 3
        template.name = "Both Template"
        template.combine_images = True
        template.optimize_images = True
        template.max_width = 1600
        template.max_height = 900
        template.max_file_size_kb = 400
        template.compression_quality = 85
        return template

    # Success Cases
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('api.routers.telegram.combine_product_images')
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('builtins.open')
    @patch('uuid.uuid4')
    def test_generate_combined_preview_success(self, mock_uuid, mock_open, mock_join, 
                                             mock_exists, mock_combine, mock_get_product, 
                                             mock_get_template, test_client, mock_db, 
                                             sample_product, sample_template_combine):
        """Test successful combined image preview generation."""
        # Setup mocks
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = sample_template_combine
        mock_exists.return_value = True
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_uuid_instance = Mock()
        mock_uuid_instance.__str__ = Mock(return_value="abc123")
        mock_uuid.return_value = mock_uuid_instance
        
        # Mock combined image generation
        mock_combine.return_value = [b"combined_image_data"]
        
        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "combined image preview" in data["message"]
        assert data["data"]["will_combine"] is True
        assert data["data"]["will_optimize"] is False
        assert data["data"]["image_count"] == 1
        assert data["data"]["original_count"] == 2
        assert len(data["data"]["preview_urls"]) == 1
        assert "/images/preview_abc123.jpg" == data["data"]["preview_urls"][0]
        
        # Verify combine_product_images was called correctly
        mock_combine.assert_called_once()
        call_args = mock_combine.call_args
        assert len(call_args[1]["image_paths"]) == 2
        assert call_args[1]["max_width"] == 1920
        assert call_args[1]["max_height"] == 1080
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    def test_optimize_only_preview_success(self, mock_get_product, mock_get_template, 
                                         test_client, mock_db, sample_product, 
                                         sample_template_optimize):
        """Test successful optimization-only preview."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = sample_template_optimize
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=2"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "original images" in data["message"]
        assert data["data"]["will_combine"] is False
        assert data["data"]["will_optimize"] is True
        assert data["data"]["image_count"] == 2
        assert len(data["data"]["preview_urls"]) == 2
        assert "/images/test_image_1.jpg" in data["data"]["preview_urls"]
        assert "/images/test_image_2.jpg" in data["data"]["preview_urls"]
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    def test_no_template_success(self, mock_get_product, mock_get_template, 
                               test_client, mock_db, sample_product):
        """Test successful preview without template (no processing)."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = None  # No template provided
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["will_combine"] is False
        assert data["data"]["will_optimize"] is False
        assert data["data"]["image_count"] == 2
        assert len(data["data"]["preview_urls"]) == 2
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('api.routers.telegram.combine_product_images')
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('builtins.open')
    @patch('uuid.uuid4')
    def test_multiple_combined_images(self, mock_uuid, mock_open, mock_join, 
                                    mock_exists, mock_combine, mock_get_product, 
                                    mock_get_template, test_client, mock_db, 
                                    sample_template_combine):
        """Test generation of multiple combined images (5+ original images)."""
        # Create product with 6 images
        product = Mock(spec=Product)
        product.id = 1
        product.images = []
        for i in range(6):
            img = Mock(spec=ProductImage)
            img.id = i + 1
            img.url = f"test_image_{i+1}.jpg"
            img.deleted_at = None
            product.images.append(img)
        
        mock_get_product.return_value = product
        mock_get_template.return_value = sample_template_combine
        mock_exists.return_value = True
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_uuid_instance = Mock()
        mock_uuid_instance.__str__ = Mock(return_value="def456")
        mock_uuid.return_value = mock_uuid_instance
        
        # Mock multiple combined images (2 groups: 4 + 2)
        mock_combine.return_value = [b"combined_1_data", b"combined_2_data"]
        
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["will_combine"] is True
        assert data["data"]["image_count"] == 2  # 2 combined images
        assert data["data"]["original_count"] == 6
        assert len(data["data"]["preview_urls"]) == 2

    # Edge Cases and Error Conditions
    
    @patch('crud.product.get_product_by_id')
    def test_product_not_found(self, mock_get_product, test_client, mock_db):
        """Test error when product is not found."""
        mock_get_product.return_value = None
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=999"
            )
        
        assert response.status_code == 404
        response_data = response.json()
        assert "Product not found" in response_data["error"]["message"]
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    def test_template_not_found(self, mock_get_product, mock_get_template, 
                              test_client, mock_db, sample_product):
        """Test error when template is not found."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = None
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=999"
            )
        
        assert response.status_code == 404
        response_data = response.json()
        assert "Template not found" in response_data["error"]["message"]
    
    @patch('crud.product.get_product_by_id')
    def test_product_no_images(self, mock_get_product, test_client, mock_db):
        """Test handling of product with no images."""
        product = Mock(spec=Product)
        product.id = 1
        product.images = []
        mock_get_product.return_value = product
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "No images to process" in data["message"]
        assert data["data"]["preview_urls"] == []
        assert data["data"]["image_count"] == 0
    
    @patch('crud.product.get_product_by_id')
    def test_product_only_deleted_images(self, mock_get_product, test_client, mock_db):
        """Test handling of product with only deleted images."""
        product = Mock(spec=Product)
        product.id = 1
        
        # Create deleted images
        deleted_image = Mock(spec=ProductImage)
        deleted_image.id = 1
        deleted_image.url = "deleted_image.jpg"
        deleted_image.deleted_at = "2023-01-01T00:00:00"
        
        product.images = [deleted_image]
        mock_get_product.return_value = product
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "No images to process" in data["message"]
        assert data["data"]["preview_urls"] == []
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    def test_single_image_no_combination(self, mock_get_product, mock_get_template, 
                                       test_client, mock_db, sample_template_combine):
        """Test that single image doesn't get combined even with combine template."""
        # Product with only one image
        product = Mock(spec=Product)
        product.id = 1
        
        image = Mock(spec=ProductImage)
        image.id = 1
        image.url = "single_image.jpg"
        image.deleted_at = None
        product.images = [image]
        
        mock_get_product.return_value = product
        mock_get_template.return_value = sample_template_combine
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["will_combine"] is False  # Single image, no combination
        assert data["data"]["image_count"] == 1
        assert "/images/single_image.jpg" in data["data"]["preview_urls"][0]
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('os.path.exists')
    @patch('os.path.join')
    def test_missing_image_files(self, mock_join, mock_exists, mock_get_product, 
                                mock_get_template, test_client, mock_db, 
                                sample_product, sample_template_combine):
        """Test handling when image files don't exist on disk."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = sample_template_combine
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_exists.return_value = False  # No files exist
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "No valid image files found" in data["message"]
        assert data["data"]["preview_urls"] == []
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('api.routers.telegram.combine_product_images')
    @patch('os.path.exists')
    def test_combine_images_failure(self, mock_exists, mock_combine, mock_get_product, 
                                  mock_get_template, test_client, mock_db, 
                                  sample_product, sample_template_combine):
        """Test handling of image combination service failure."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = sample_template_combine
        mock_exists.return_value = True
        
        # Mock combination failure
        mock_combine.side_effect = Exception("Image combination failed")
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to generate image preview" in response_data["error"]["message"]
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('api.routers.telegram.combine_product_images')
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('builtins.open')
    def test_file_write_failure(self, mock_open, mock_join, mock_exists, mock_combine, 
                               mock_get_product, mock_get_template, test_client, 
                               mock_db, sample_product, sample_template_combine):
        """Test handling of file write failure."""
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = sample_template_combine
        mock_exists.return_value = True
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_combine.return_value = [b"combined_image_data"]
        
        # Mock file write failure
        mock_open.side_effect = IOError("Disk full")
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to generate image preview" in response_data["error"]["message"]

    # Parameter Validation Tests
    
    def test_missing_product_id(self, test_client):
        """Test error when product_id parameter is missing."""
        response = test_client.post("/api/v1/telegram/image-preview")
        
        assert response.status_code == 422
        response_data = response.json()
        error_details = response_data["error"]["details"]["validation_errors"]
        assert any("product_id" in str(error).lower() for error in error_details)
    
    def test_invalid_product_id_type(self, test_client):
        """Test error when product_id is not an integer."""
        response = test_client.post(
            "/api/v1/telegram/image-preview?product_id=not_a_number"
        )
        
        assert response.status_code == 422
    
    def test_invalid_template_id_type(self, test_client):
        """Test error when template_id is not an integer."""
        response = test_client.post(
            "/api/v1/telegram/image-preview?product_id=1&template_id=not_a_number"
        )
        
        assert response.status_code == 422

    # Database Error Tests
    
    @patch('crud.product.get_product_by_id')
    def test_database_error(self, mock_get_product, test_client, mock_db):
        """Test handling of database errors."""
        mock_get_product.side_effect = Exception("Database connection failed")
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1"
            )
        
        assert response.status_code == 500
        response_data = response.json()
        assert "Failed to generate image preview" in response_data["error"]["message"]

    # Template Settings Edge Cases
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    def test_template_combine_disabled_optimize_disabled(self, mock_get_product, 
                                                       mock_get_template, test_client, 
                                                       mock_db, sample_product):
        """Test template with both combination and optimization disabled."""
        template = Mock(spec=MessageTemplate)
        template.id = 1
        template.combine_images = False
        template.optimize_images = False
        template.max_width = 1920
        template.max_height = 1080
        
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = template
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["will_combine"] is False
        assert data["data"]["will_optimize"] is False
        assert data["data"]["image_count"] == 2
    
    @patch('crud.template.get_template_by_id')
    @patch('crud.product.get_product_by_id')
    @patch('api.routers.telegram.combine_product_images')
    @patch('os.path.exists')
    @patch('os.path.join')
    @patch('builtins.open')
    @patch('uuid.uuid4')
    def test_extreme_template_settings(self, mock_uuid, mock_open, mock_join, 
                                     mock_exists, mock_combine, mock_get_product, 
                                     mock_get_template, test_client, mock_db, 
                                     sample_product):
        """Test template with extreme settings values."""
        template = Mock(spec=MessageTemplate)
        template.id = 1
        template.combine_images = True
        template.optimize_images = True
        template.max_width = 4000  # Maximum allowed
        template.max_height = 200   # Minimum allowed
        template.max_file_size_kb = 50  # Minimum allowed
        template.compression_quality = 100  # Maximum allowed
        
        mock_get_product.return_value = sample_product
        mock_get_template.return_value = template
        mock_exists.return_value = True
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_uuid_instance = Mock()
        mock_uuid_instance.__str__ = Mock(return_value="extreme123")
        mock_uuid.return_value = mock_uuid_instance
        mock_combine.return_value = [b"extreme_combined_data"]
        
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        with patch('database.session.get_db', return_value=mock_db):
            response = test_client.post(
                "/api/v1/telegram/image-preview?product_id=1&template_id=1"
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["data"]["will_combine"] is True
        
        # Verify extreme settings were passed to combine function
        mock_combine.assert_called_once()
        call_args = mock_combine.call_args
        assert call_args[1]["max_width"] == 4000
        assert call_args[1]["max_height"] == 200