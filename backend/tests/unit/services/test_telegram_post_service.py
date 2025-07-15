"""
Tests for telegram_post_service.py
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from services.telegram_post_service import TelegramPostService, telegram_post_service
from models.product import Product, TelegramChannel, TelegramPost, Image
from schemas.telegram import TelegramPostCreate, PostStatus
from exceptions.base import ValidationException, ExternalServiceException


class TestTelegramPostServiceInit:
    """Test TelegramPostService initialization"""
    
    def test_init(self):
        """Test service initialization"""
        service = TelegramPostService()
        assert service.telegram_service is not None
        assert service.template_renderer is not None


class TestTelegramPostServicePreviewPost:
    """Test preview_post method"""
    
    @pytest.mark.asyncio
    async def test_preview_post_product_not_found(self):
        """Test preview_post with non-existent product"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=None):
            with pytest.raises(ValidationException) as exc_info:
                await service.preview_post(mock_db, 999)
            
            assert "Product not found" in str(exc_info.value)
            assert exc_info.value.details["product_id"] == 999
    
    @pytest.mark.asyncio
    async def test_preview_post_channel_not_found(self):
        """Test preview_post with non-existent channel"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=None):
            
            with pytest.raises(ValidationException) as exc_info:
                await service.preview_post(mock_db, 1, channel_id=999)
            
            assert "Channel not found" in str(exc_info.value)
            assert exc_info.value.details["channel_id"] == 999
    
    @pytest.mark.asyncio
    async def test_preview_post_template_not_found(self):
        """Test preview_post with non-existent template"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_template_by_id', return_value=None):
            
            with pytest.raises(ValidationException) as exc_info:
                await service.preview_post(mock_db, 1, template_id=999)
            
            assert "Template not found" in str(exc_info.value)
            assert exc_info.value.details["template_id"] == 999
    
    @pytest.mark.asyncio
    async def test_preview_post_with_custom_template(self):
        """Test preview_post with custom template content"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        # Mock product with images
        mock_image1 = Mock(spec=Image)
        mock_image1.deleted_at = None
        mock_image2 = Mock(spec=Image)
        mock_image2.deleted_at = datetime.now()  # Deleted image
        
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        mock_product.images = [mock_image1, mock_image2]
        
        custom_template = "Product: {product_name}"
        rendered_content = "Product: Test Product"
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content):
            
            result = await service.preview_post(mock_db, 1, template_content=custom_template)
            
            assert result["rendered_content"] == rendered_content
            assert result["template_used"] == custom_template
            assert result["product_name"] == "Test Product"
            assert result["channel_name"] is None
            assert result["will_send_photos"] is True
            assert result["photo_count"] == 1  # Only non-deleted images
    
    @pytest.mark.asyncio
    async def test_preview_post_with_template_id(self):
        """Test preview_post with template ID"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        mock_product.images = []
        
        mock_template = Mock()
        mock_template.template_content = "Template: {product_name}"
        
        rendered_content = "Template: Test Product"
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_template_by_id', return_value=mock_template), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content):
            
            result = await service.preview_post(mock_db, 1, template_id=1)
            
            assert result["rendered_content"] == rendered_content
            assert result["template_used"] == "Template: {product_name}"
            assert result["photo_count"] == 0
    
    @pytest.mark.asyncio
    async def test_preview_post_with_channel_template(self):
        """Test preview_post with channel's default template"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        mock_product.images = []
        
        mock_template = Mock()
        mock_template.template_content = "Channel template: {product_name}"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Test Channel"
        mock_channel.send_photos = False
        mock_channel.template_id = 1
        
        rendered_content = "Channel template: Test Product"
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_template_by_id', return_value=mock_template), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content):
            
            result = await service.preview_post(mock_db, 1, channel_id=1)
            
            assert result["rendered_content"] == rendered_content
            assert result["template_used"] == "Channel template: {product_name}"
            assert result["channel_name"] == "Test Channel"
            assert result["will_send_photos"] is False
    
    @pytest.mark.asyncio
    async def test_preview_post_with_default_template(self):
        """Test preview_post falling back to default template"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        mock_product.images = []
        
        rendered_content = "📦 New Product: Test Product"
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content):
            
            result = await service.preview_post(mock_db, 1)
            
            assert result["rendered_content"] == rendered_content
            assert "📦 New Product:" in result["template_used"]
    
    @pytest.mark.asyncio
    async def test_preview_post_template_rendering_error(self):
        """Test preview_post with template rendering error"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.name = "Test Product"
        mock_product.images = []
        
        template_content = "Bad template: {invalid_field}"
        
        with patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch.object(service.template_renderer, 'render_template', side_effect=Exception("Invalid field")):
            
            with pytest.raises(ValidationException) as exc_info:
                await service.preview_post(mock_db, 1, template_content=template_content)
            
            assert "Template rendering failed" in str(exc_info.value)
            assert exc_info.value.details["template_content"] == template_content
            assert "Invalid field" in exc_info.value.details["error"]


class TestTelegramPostServiceSendPost:
    """Test send_post method"""
    
    @pytest.mark.asyncio
    async def test_send_post_telegram_disabled(self):
        """Test send_post with telegram service disabled"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=False):
            with pytest.raises(ValidationException) as exc_info:
                await service.send_post(mock_db, 1, [1])
            
            assert "Telegram service is disabled" in str(exc_info.value)
            assert exc_info.value.details["telegram_enabled"] is False
    
    @pytest.mark.asyncio
    async def test_send_post_product_not_found(self):
        """Test send_post with non-existent product"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=None):
            
            with pytest.raises(ValidationException) as exc_info:
                await service.send_post(mock_db, 999, [1])
            
            assert "Product not found" in str(exc_info.value)
            assert exc_info.value.details["product_id"] == 999
    
    @pytest.mark.asyncio
    async def test_send_post_channel_not_found(self):
        """Test send_post with non-existent channel"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=None):
            
            result = await service.send_post(mock_db, 1, [999])
            
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Channel 999 not found" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_send_post_inactive_channel(self):
        """Test send_post with inactive channel"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Inactive Channel"
        mock_channel.is_active = False
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel):
            
            result = await service.send_post(mock_db, 1, [1])
            
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Channel Inactive Channel is not active" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_send_post_success(self):
        """Test successful send_post"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.id = 1
        mock_channel.name = "Test Channel"
        mock_channel.is_active = True
        mock_channel.template_id = 1
        
        mock_template = Mock()
        mock_template.template_content = "Test template: {product_name}"
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        
        rendered_content = "Test template: Test Product"
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_template_by_id', return_value=mock_template), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content), \
             patch('services.telegram_post_service.create_post', return_value=mock_post), \
             patch.object(service, '_send_post_to_telegram', new_callable=AsyncMock):
            
            result = await service.send_post(mock_db, 1, [1])
            
            assert result["success_count"] == 1
            assert result["failed_count"] == 0
            assert len(result["posts_created"]) == 1
            assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_send_post_template_rendering_error(self):
        """Test send_post with template rendering error"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.id = 1
        mock_channel.name = "Test Channel"
        mock_channel.is_active = True
        mock_channel.template_id = 1
        
        mock_template = Mock()
        mock_template.template_content = "Bad template: {invalid_field}"
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_template_by_id', return_value=mock_template), \
             patch.object(service.template_renderer, 'render_template', side_effect=Exception("Invalid field")):
            
            result = await service.send_post(mock_db, 1, [1])
            
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Template rendering failed for channel Test Channel" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_send_post_with_custom_template(self):
        """Test send_post with custom template content"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_product = Mock(spec=Product)
        mock_product.id = 1
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.id = 1
        mock_channel.name = "Test Channel"
        mock_channel.is_active = True
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        
        custom_template = "Custom: {product_name}"
        rendered_content = "Custom: Test Product"
        
        with patch.object(service.telegram_service, 'is_enabled', return_value=True), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch.object(service.template_renderer, 'render_template', return_value=rendered_content), \
             patch('services.telegram_post_service.create_post', return_value=mock_post), \
             patch.object(service, '_send_post_to_telegram', new_callable=AsyncMock):
            
            result = await service.send_post(mock_db, 1, [1], template_content=custom_template)
            
            assert result["success_count"] == 1
            assert result["failed_count"] == 0


class TestTelegramPostServiceSendPostToTelegram:
    """Test _send_post_to_telegram method"""
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_text_only(self):
        """Test sending text-only post to telegram"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = False
        mock_channel.disable_notification = False
        mock_channel.disable_web_page_preview = True
        
        mock_product = Mock(spec=Product)
        mock_product.images = []
        
        telegram_result = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        with patch.object(service.telegram_service, 'send_message', return_value=telegram_result), \
             patch('services.telegram_post_service.update_post_status') as mock_update, \
             patch.object(mock_db, 'add'), \
             patch.object(mock_db, 'commit'):
            
            await service._send_post_to_telegram(mock_db, mock_post, mock_channel, mock_product)
            
            # Verify message was sent with correct parameters
            service.telegram_service.send_message.assert_called_once_with(
                chat_id="@test_channel",
                text="Test message",
                parse_mode="HTML",
                disable_web_page_preview=True,
                disable_notification=False
            )
            
            # Verify post status was updated
            mock_update.assert_called_once_with(mock_db, 1, PostStatus.SENT, message_id=123)
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_single_photo(self):
        """Test sending post with single photo"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = True
        mock_channel.disable_notification = False
        
        mock_image = Mock(spec=Image)
        mock_image.url = "test.jpg"
        mock_image.deleted_at = None
        
        mock_product = Mock(spec=Product)
        mock_product.images = [mock_image]
        
        telegram_result = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_filename = tmp_file.name
            
        try:
            with patch('os.path.join', return_value=tmp_filename), \
                 patch('os.path.exists', return_value=True), \
                 patch.object(service.telegram_service, 'send_photo', return_value=telegram_result), \
                 patch('services.telegram_post_service.update_post_status'), \
                 patch.object(mock_db, 'add'), \
                 patch.object(mock_db, 'commit'):
                
                await service._send_post_to_telegram(mock_db, mock_post, mock_channel, mock_product)
                
                # Verify photo was sent
                service.telegram_service.send_photo.assert_called_once()
        finally:
            try:
                os.unlink(tmp_filename)
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors on Windows
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_multiple_photos(self):
        """Test sending post with multiple photos"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = True
        mock_channel.disable_notification = False
        
        mock_image1 = Mock(spec=Image)
        mock_image1.url = "test1.jpg"
        mock_image1.deleted_at = None
        
        mock_image2 = Mock(spec=Image)
        mock_image2.url = "test2.jpg"
        mock_image2.deleted_at = None
        
        mock_product = Mock(spec=Product)
        mock_product.images = [mock_image1, mock_image2]
        
        telegram_result = {
            "ok": True,
            "result": [{"message_id": 123}, {"message_id": 124}]
        }
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            file1 = os.path.join(tmp_dir, "test1.jpg")
            file2 = os.path.join(tmp_dir, "test2.jpg")
            
            with open(file1, 'wb') as f:
                f.write(b"fake image data 1")
            with open(file2, 'wb') as f:
                f.write(b"fake image data 2")
            
            # Store original function before mocking
            original_join = os.path.join
            
            # Mock the specific function that's called in the service
            def mock_path_join(*args):
                if len(args) == 2 and args[0] == "images":
                    return original_join(tmp_dir, args[1])
                return original_join(*args)
            
            with patch('services.telegram_post_service.os.path.join', side_effect=mock_path_join), \
                 patch('os.path.exists', return_value=True), \
                 patch.object(service.telegram_service, 'send_media_group', return_value=telegram_result), \
                 patch('services.telegram_post_service.update_post_status') as mock_update, \
                 patch.object(mock_db, 'add'), \
                 patch.object(mock_db, 'commit'):
                
                await service._send_post_to_telegram(mock_db, mock_post, mock_channel, mock_product)
                
                # Verify media group was sent
                service.telegram_service.send_media_group.assert_called_once()
                
                # Verify post status was updated with first message ID
                mock_update.assert_called_once_with(mock_db, 1, PostStatus.SENT, message_id=123)
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_missing_image_file(self):
        """Test sending post when image file is missing"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = True
        mock_channel.disable_notification = False
        mock_channel.disable_web_page_preview = True
        
        mock_image = Mock(spec=Image)
        mock_image.url = "missing.jpg"
        mock_image.deleted_at = None
        
        mock_product = Mock(spec=Product)
        mock_product.images = [mock_image]
        
        telegram_result = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        with patch('os.path.join', return_value="images/missing.jpg"), \
             patch('os.path.exists', return_value=False), \
             patch.object(service.telegram_service, 'send_message', return_value=telegram_result), \
             patch('services.telegram_post_service.update_post_status'), \
             patch.object(mock_db, 'add'), \
             patch.object(mock_db, 'commit'):
            
            await service._send_post_to_telegram(mock_db, mock_post, mock_channel, mock_product)
            
            # Should fall back to text message when no photos available
            service.telegram_service.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_with_overrides(self):
        """Test sending post with parameter overrides"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = True  # Will be overridden to False
        mock_channel.disable_notification = False  # Will be overridden to True
        mock_channel.disable_web_page_preview = False
        
        mock_product = Mock(spec=Product)
        mock_product.images = []
        
        telegram_result = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        with patch.object(service.telegram_service, 'send_message', return_value=telegram_result), \
             patch('services.telegram_post_service.update_post_status'), \
             patch.object(mock_db, 'add'), \
             patch.object(mock_db, 'commit'):
            
            await service._send_post_to_telegram(
                mock_db, mock_post, mock_channel, mock_product,
                send_photos_override=False,
                disable_notification_override=True
            )
            
            # Verify overrides were applied
            service.telegram_service.send_message.assert_called_once_with(
                chat_id="@test_channel",
                text="Test message",
                parse_mode="HTML",
                disable_web_page_preview=False,
                disable_notification=True  # Override applied
            )
    
    @pytest.mark.asyncio
    async def test_send_post_to_telegram_exception(self):
        """Test _send_post_to_telegram with exception"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.rendered_content = "Test message"
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Test Channel"
        mock_channel.chat_id = "@test_channel"
        mock_channel.send_photos = False
        mock_channel.disable_notification = False
        mock_channel.disable_web_page_preview = True
        
        mock_product = Mock(spec=Product)
        mock_product.images = []
        
        error_exception = ExternalServiceException(
            service="telegram",
            message="API error"
        )
        
        with patch.object(service.telegram_service, 'send_message', side_effect=error_exception), \
             patch('services.telegram_post_service.update_post_status') as mock_update, \
             patch.object(mock_db, 'commit'):
            
            with pytest.raises(ExternalServiceException):
                await service._send_post_to_telegram(mock_db, mock_post, mock_channel, mock_product)
            
            # Verify post status was updated to failed
            mock_update.assert_called_once_with(
                mock_db, 1, PostStatus.FAILED, 
                error_message="API error"
            )


class TestTelegramPostServiceRetryFailedPosts:
    """Test retry_failed_posts method"""
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts_no_failed_posts(self):
        """Test retry_failed_posts when no failed posts exist"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        result = await service.retry_failed_posts(mock_db)
        
        assert result["retried_count"] == 0
        assert result["success_count"] == 0
        assert result["failed_count"] == 0
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts_success(self):
        """Test successful retry of failed posts"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.channel_id = 1
        mock_post.product_id = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_post]
        mock_db.query.return_value = mock_query
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Test Channel"
        mock_channel.is_active = True
        
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch.object(service, '_send_post_to_telegram', new_callable=AsyncMock):
            
            result = await service.retry_failed_posts(mock_db)
            
            assert result["retried_count"] == 1
            assert result["success_count"] == 1
            assert result["failed_count"] == 0
            assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts_missing_channel(self):
        """Test retry with missing channel"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.channel_id = 1
        mock_post.product_id = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_post]
        mock_db.query.return_value = mock_query
        
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_channel_by_id', return_value=None), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product):
            
            result = await service.retry_failed_posts(mock_db)
            
            assert result["retried_count"] == 1
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Post 1: Missing channel or product" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts_inactive_channel(self):
        """Test retry with inactive channel"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.channel_id = 1
        mock_post.product_id = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_post]
        mock_db.query.return_value = mock_query
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Inactive Channel"
        mock_channel.is_active = False
        
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product):
            
            result = await service.retry_failed_posts(mock_db)
            
            assert result["retried_count"] == 1
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Post 1: Channel Inactive Channel is not active" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_retry_failed_posts_exception(self):
        """Test retry with exception during retry"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_post = Mock(spec=TelegramPost)
        mock_post.id = 1
        mock_post.channel_id = 1
        mock_post.product_id = 1
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_post]
        mock_db.query.return_value = mock_query
        
        mock_channel = Mock(spec=TelegramChannel)
        mock_channel.name = "Test Channel"
        mock_channel.is_active = True
        
        mock_product = Mock(spec=Product)
        
        with patch('services.telegram_post_service.get_channel_by_id', return_value=mock_channel), \
             patch('services.telegram_post_service.get_product_by_id', return_value=mock_product), \
             patch.object(service, '_send_post_to_telegram', side_effect=Exception("Retry failed")):
            
            result = await service.retry_failed_posts(mock_db)
            
            assert result["retried_count"] == 1
            assert result["success_count"] == 0
            assert result["failed_count"] == 1
            assert "Post 1: Retry failed - Retry failed" in result["errors"]


class TestTelegramPostServiceAutoPost:
    """Test auto_post_product method"""
    
    @pytest.mark.asyncio
    async def test_auto_post_product_no_channels(self):
        """Test auto_post_product when no auto-post channels exist"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        
        result = await service.auto_post_product(mock_db, 1)
        
        assert result["success_count"] == 0
        assert result["failed_count"] == 0
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_auto_post_product_success(self):
        """Test successful auto_post_product"""
        service = TelegramPostService()
        mock_db = Mock(spec=Session)
        
        mock_channel1 = Mock(spec=TelegramChannel)
        mock_channel1.id = 1
        mock_channel2 = Mock(spec=TelegramChannel)
        mock_channel2.id = 2
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_channel1, mock_channel2]
        mock_db.query.return_value = mock_query
        
        expected_result = {
            "success_count": 2,
            "failed_count": 0,
            "errors": []
        }
        
        with patch.object(service, 'send_post', return_value=expected_result) as mock_send_post:
            result = await service.auto_post_product(mock_db, 1)
            
            # Verify send_post was called with correct channel IDs
            mock_send_post.assert_called_once_with(
                db=mock_db,
                product_id=1,
                channel_ids=[1, 2]
            )
            
            assert result == expected_result


class TestTelegramPostServiceGlobalInstance:
    """Test global service instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert telegram_post_service is not None
        assert isinstance(telegram_post_service, TelegramPostService)
    
    def test_global_instance_is_singleton(self):
        """Test global instance behavior"""
        # Import again to ensure it's the same instance
        from services.telegram_post_service import telegram_post_service as service2
        assert telegram_post_service is service2