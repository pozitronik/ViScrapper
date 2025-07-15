"""
Tests for telegram_service.py
"""
import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import httpx
from pathlib import Path

from services.telegram_service import TelegramService, telegram_service
from exceptions.base import ExternalServiceException, ValidationException


def safe_unlink(filepath):
    """Safely delete a file, handling Windows permission errors"""
    try:
        os.unlink(filepath)
    except (OSError, PermissionError):
        pass  # Ignore cleanup errors on Windows


class TestTelegramServiceInit:
    """Test TelegramService initialization"""
    
    def test_init_with_bot_token(self):
        """Test initialization with bot token"""
        service = TelegramService(bot_token="test_token")
        assert service.bot_token == "test_token"
        assert service.enabled is True
        assert service.base_url == "https://api.telegram.org/bottest_token"
        assert service._client is not None
    
    def test_init_with_env_bot_token(self):
        """Test initialization with environment bot token"""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "env_token"}):
            service = TelegramService()
            assert service.bot_token == "env_token"
            assert service.enabled is True
            assert service.base_url == "https://api.telegram.org/botenv_token"
    
    def test_init_without_bot_token(self):
        """Test initialization without bot token"""
        with patch.dict(os.environ, {}, clear=True):
            service = TelegramService()
            assert service.bot_token is None
            assert service.enabled is False
            assert service._client is None
    
    def test_init_with_none_bot_token(self):
        """Test initialization with None bot token"""
        with patch.dict(os.environ, {}, clear=True):
            service = TelegramService(bot_token=None)
            assert service.bot_token is None
            assert service.enabled is False
            assert service._client is None


class TestTelegramServiceHandleRateLimit:
    """Test _handle_rate_limit_retry method"""
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_not_429(self):
        """Test rate limit handling when status is not 429"""
        service = TelegramService(bot_token="test_token")
        response = Mock()
        response.status_code = 400
        
        result = await service._handle_rate_limit_retry(response, "test_operation")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_success(self):
        """Test successful rate limit handling"""
        service = TelegramService(bot_token="test_token")
        response = Mock()
        response.status_code = 429
        response.json.return_value = {
            "parameters": {"retry_after": 10}
        }
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await service._handle_rate_limit_retry(response, "test_operation")
            
            assert result == {"retry": True, "retry_after": 10}
            mock_sleep.assert_called_once_with(11)  # retry_after + 1
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_default_retry_after(self):
        """Test rate limit handling with default retry_after"""
        service = TelegramService(bot_token="test_token")
        response = Mock()
        response.status_code = 429
        response.json.return_value = {"parameters": {}}
        
        with patch('asyncio.sleep') as mock_sleep:
            result = await service._handle_rate_limit_retry(response, "test_operation")
            
            assert result == {"retry": True, "retry_after": 5}
            mock_sleep.assert_called_once_with(6)  # default 5 + 1
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_json_decode_error(self):
        """Test rate limit handling with JSON decode error"""
        service = TelegramService(bot_token="test_token")
        response = Mock()
        response.status_code = 429
        response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        result = await service._handle_rate_limit_retry(response, "test_operation")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_handle_rate_limit_key_error(self):
        """Test rate limit handling with missing parameters structure - uses default retry_after"""
        service = TelegramService(bot_token="test_token")
        response = Mock()
        response.status_code = 429
        response.json.return_value = {"invalid": "structure"}
        
        result = await service._handle_rate_limit_retry(response, "test_operation")
        # Should return retry=True with default retry_after=5 when structure is missing
        assert result is not None
        assert result["retry"] is True
        assert result["retry_after"] == 5


class TestTelegramServiceSendMessage:
    """Test send_message method"""
    
    @pytest.mark.asyncio
    async def test_send_message_disabled_service(self):
        """Test send_message with disabled service"""
        service = TelegramService(bot_token=None)
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_message("test_chat", "test message")
        
        assert "Telegram service is disabled" in str(exc_info.value)
        assert exc_info.value.details["bot_token_configured"] is False
    
    @pytest.mark.asyncio
    async def test_send_message_empty_chat_id(self):
        """Test send_message with empty chat_id"""
        service = TelegramService(bot_token="test_token")
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_message("", "test message")
        
        assert "Chat ID is required" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_empty_text(self):
        """Test send_message with empty text"""
        service = TelegramService(bot_token="test_token")
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_message("test_chat", "")
        
        assert "Message text must be 1-4096 characters" in str(exc_info.value)
        assert exc_info.value.details["text_length"] == 0
    
    @pytest.mark.asyncio
    async def test_send_message_text_too_long(self):
        """Test send_message with text too long"""
        service = TelegramService(bot_token="test_token")
        long_text = "a" * 4097
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_message("test_chat", long_text)
        
        assert "Message text must be 1-4096 characters" in str(exc_info.value)
        assert exc_info.value.details["text_length"] == 4097
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123}
        }
        
        with patch.object(service._client, 'post', return_value=mock_response):
            result = await service.send_message("test_chat", "test message")
            
            assert result["ok"] is True
            assert result["result"]["message_id"] == 123
    
    @pytest.mark.asyncio
    async def test_send_message_with_optional_params(self):
        """Test message sending with optional parameters"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        
        with patch.object(service._client, 'post', return_value=mock_response) as mock_post:
            await service.send_message(
                "test_chat", 
                "test message",
                parse_mode="Markdown",
                disable_web_page_preview=False,
                disable_notification=True,
                reply_to_message_id=456
            )
            
            # Verify the request data
            call_args = mock_post.call_args
            assert call_args[1]["data"]["parse_mode"] == "Markdown"
            assert call_args[1]["data"]["disable_web_page_preview"] is False
            assert call_args[1]["data"]["disable_notification"] is True
            assert call_args[1]["data"]["reply_to_message_id"] == 456
    
    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Test message sending with API error"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Bad Request"
        }
        
        with patch.object(service._client, 'post', return_value=mock_response):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.send_message("test_chat", "test message")
            
            assert exc_info.value.details["service"] == "telegram"
            assert "Bad Request" in str(exc_info.value)
            assert exc_info.value.details["error_code"] == 400
    
    @pytest.mark.asyncio
    async def test_send_message_http_error(self):
        """Test message sending with HTTP error"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        with patch.object(service._client, 'post', return_value=mock_response):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.send_message("test_chat", "test message")
            
            assert exc_info.value.details["service"] == "telegram"
            assert exc_info.value.details["status_code"] == 404
    
    @pytest.mark.asyncio
    async def test_send_message_rate_limit_retry_success(self):
        """Test message sending with rate limit retry success"""
        service = TelegramService(bot_token="test_token")
        
        # First response: rate limit, second response: success
        mock_responses = [
            Mock(status_code=429, json=Mock(return_value={"parameters": {"retry_after": 1}})),
            Mock(status_code=200, json=Mock(return_value={"ok": True, "result": {"message_id": 123}}))
        ]
        
        with patch.object(service._client, 'post', side_effect=mock_responses), \
             patch('asyncio.sleep') as mock_sleep:
            
            result = await service.send_message("test_chat", "test message")
            
            assert result["ok"] is True
            assert result["result"]["message_id"] == 123
            mock_sleep.assert_called_once_with(2)  # retry_after + 1
    
    @pytest.mark.asyncio
    async def test_send_message_rate_limit_exhausted(self):
        """Test message sending with rate limit retries exhausted"""
        service = TelegramService(bot_token="test_token")
        
        # All responses return rate limit
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"parameters": {"retry_after": 1}}
        
        with patch.object(service._client, 'post', return_value=mock_response), \
             patch('asyncio.sleep'):
            
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.send_message("test_chat", "test message", max_retries=2)
            
            # Current behavior: raises HTTP error 429 instead of exhausted retries message
            assert "HTTP error 429" in str(exc_info.value)
            assert exc_info.value.details["status_code"] == 429
    
    @pytest.mark.asyncio
    async def test_send_message_request_error(self):
        """Test message sending with request error"""
        service = TelegramService(bot_token="test_token")
        
        with patch.object(service._client, 'post', side_effect=httpx.RequestError("Connection failed")):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.send_message("test_chat", "test message")
            
            assert exc_info.value.details["service"] == "telegram"
            assert "Network error" in str(exc_info.value)
            assert exc_info.value.details["operation"] == "send_message"


class TestTelegramServiceSendPhoto:
    """Test send_photo method"""
    
    @pytest.mark.asyncio
    async def test_send_photo_disabled_service(self):
        """Test send_photo with disabled service"""
        service = TelegramService(bot_token=None)
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_photo("test_chat", "test.jpg")
        
        assert "Telegram service is disabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_photo_file_not_found(self):
        """Test send_photo with non-existent file"""
        service = TelegramService(bot_token="test_token")
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_photo("test_chat", "/nonexistent/file.jpg")
        
        assert "Photo file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_photo_caption_too_long(self):
        """Test send_photo with caption too long"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_filename = tmp_file.name
            
        try:
            long_caption = "a" * 1025
            with pytest.raises(ValidationException) as exc_info:
                await service.send_photo("test_chat", tmp_filename, caption=long_caption)
            
            assert "Photo caption must be up to 1024 characters" in str(exc_info.value)
            assert exc_info.value.details["caption_length"] == 1025
        finally:
            safe_unlink(tmp_filename)
    
    @pytest.mark.asyncio
    async def test_send_photo_success(self):
        """Test successful photo sending"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_filename = tmp_file.name
            
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "result": {"message_id": 123}
            }
            
            with patch.object(service._client, 'post', return_value=mock_response):
                result = await service.send_photo("test_chat", tmp_filename)
                
                assert result["ok"] is True
                assert result["result"]["message_id"] == 123
        finally:
            safe_unlink(tmp_filename)
    
    @pytest.mark.asyncio
    async def test_send_photo_with_caption(self):
        """Test photo sending with caption"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_filename = tmp_file.name
            
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
            
            with patch.object(service._client, 'post', return_value=mock_response) as mock_post:
                await service.send_photo("test_chat", tmp_filename, caption="Test caption")
                
                # Verify the request data
                call_args = mock_post.call_args
                assert call_args[1]["data"]["caption"] == "Test caption"
                assert call_args[1]["data"]["parse_mode"] == "HTML"
        finally:
            safe_unlink(tmp_filename)
    
    @pytest.mark.asyncio
    async def test_send_photo_api_error(self):
        """Test photo sending with API error"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_filename = tmp_file.name
            
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": False,
                "description": "Photo upload failed"
            }
            
            with patch.object(service._client, 'post', return_value=mock_response):
                with pytest.raises(ExternalServiceException) as exc_info:
                    await service.send_photo("test_chat", tmp_filename)
                
                assert "Photo upload failed" in str(exc_info.value)
        finally:
            safe_unlink(tmp_filename)
    
    @pytest.mark.asyncio
    async def test_send_photo_rate_limit_retry(self):
        """Test photo sending with rate limit retry"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary file and get its name
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        tmp_file.write(b"fake image data")
        tmp_file.flush()
        tmp_file_path = tmp_file.name
        tmp_file.close()  # Close the file before using it
        
        try:
            # First response: rate limit, second response: success
            mock_responses = [
                Mock(status_code=429, json=Mock(return_value={"parameters": {"retry_after": 1}})),
                Mock(status_code=200, json=Mock(return_value={"ok": True, "result": {"message_id": 123}}))
            ]
            
            with patch.object(service._client, 'post', side_effect=mock_responses), \
                 patch('asyncio.sleep') as mock_sleep:
                
                result = await service.send_photo("test_chat", tmp_file_path)
                
                assert result["ok"] is True
                assert result["result"]["message_id"] == 123
                mock_sleep.assert_called_once_with(2)  # retry_after + 1
        finally:
            safe_unlink(tmp_file_path)
    
    @pytest.mark.asyncio
    async def test_send_photo_file_not_found_during_send(self):
        """Test photo sending with file not found during send"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            tmp_path = tmp_file.name
        
        # Delete the file after creation but before sending
        os.unlink(tmp_path)
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_photo("test_chat", tmp_path)
        
        assert "Photo file not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_photo_request_error(self):
        """Test photo sending with request error"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            
            try:
                with patch.object(service._client, 'post', side_effect=httpx.RequestError("Connection failed")):
                    with pytest.raises(ExternalServiceException) as exc_info:
                        await service.send_photo("test_chat", tmp_file.name)
                    
                    assert "Network error" in str(exc_info.value)
                    assert exc_info.value.details["operation"] == "send_photo"
            finally:
                safe_unlink(tmp_file.name)


class TestTelegramServiceSendMediaGroup:
    """Test send_media_group method"""
    
    @pytest.mark.asyncio
    async def test_send_media_group_disabled_service(self):
        """Test send_media_group with disabled service"""
        service = TelegramService(bot_token=None)
        
        with pytest.raises(ValidationException) as exc_info:
            await service.send_media_group("test_chat", ["test1.jpg", "test2.jpg"])
        
        assert "Telegram service is disabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_media_group_invalid_count(self):
        """Test send_media_group with invalid photo count"""
        service = TelegramService(bot_token="test_token")
        
        # Test with 1 photo (too few)
        with pytest.raises(ValidationException) as exc_info:
            await service.send_media_group("test_chat", ["test1.jpg"])
        
        assert "Media group must contain 2-10 photos" in str(exc_info.value)
        assert exc_info.value.details["media_count"] == 1
        
        # Test with 11 photos (too many)
        many_photos = [f"test{i}.jpg" for i in range(11)]
        with pytest.raises(ValidationException) as exc_info:
            await service.send_media_group("test_chat", many_photos)
        
        assert "Media group must contain 2-10 photos" in str(exc_info.value)
        assert exc_info.value.details["media_count"] == 11
        
        # Test with empty list
        with pytest.raises(ValidationException) as exc_info:
            await service.send_media_group("test_chat", [])
        
        assert "Media group must contain 2-10 photos" in str(exc_info.value)
        assert exc_info.value.details["media_count"] == 0
    
    @pytest.mark.asyncio
    async def test_send_media_group_file_not_found(self):
        """Test send_media_group with non-existent file"""
        service = TelegramService(bot_token="test_token")
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(b"fake image data")
            tmp_file.flush()
            
            try:
                with pytest.raises(ValidationException) as exc_info:
                    await service.send_media_group("test_chat", [tmp_file.name, "/nonexistent/file.jpg"])
                
                assert "Photo file not found" in str(exc_info.value)
                assert exc_info.value.details["photo_path"] == "/nonexistent/file.jpg"
            finally:
                safe_unlink(tmp_file.name)
    
    @pytest.mark.asyncio
    async def test_send_media_group_success(self):
        """Test successful media group sending"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(3):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": True,
                "result": [{"message_id": 123}, {"message_id": 124}, {"message_id": 125}]
            }
            
            with patch.object(service._client, 'post', return_value=mock_response):
                result = await service.send_media_group("test_chat", tmp_files)
                
                assert result["ok"] is True
                assert len(result["result"]) == 3
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)
    
    @pytest.mark.asyncio
    async def test_send_media_group_with_caption(self):
        """Test media group sending with caption"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(2):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True, "result": [{"message_id": 123}]}
            
            with patch.object(service._client, 'post', return_value=mock_response) as mock_post:
                await service.send_media_group("test_chat", tmp_files, caption="Test caption")
                
                # Verify the request data contains proper media JSON
                call_args = mock_post.call_args
                media_json = call_args[1]["data"]["media"]
                media_array = json.loads(media_json)
                
                # First photo should have caption
                assert media_array[0]["caption"] == "Test caption"
                assert media_array[0]["parse_mode"] == "HTML"
                
                # Second photo should not have caption
                assert "caption" not in media_array[1]
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)
    
    @pytest.mark.asyncio
    async def test_send_media_group_api_error(self):
        """Test media group sending with API error"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(2):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "ok": False,
                "error_code": 400,
                "description": "Media group upload failed"
            }
            
            with patch.object(service._client, 'post', return_value=mock_response):
                with pytest.raises(ExternalServiceException) as exc_info:
                    await service.send_media_group("test_chat", tmp_files)
                
                assert "Media group upload failed" in str(exc_info.value)
                assert exc_info.value.details["error_code"] == 400
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)
    
    @pytest.mark.asyncio
    async def test_send_media_group_rate_limit_retry(self):
        """Test media group sending with rate limit retry"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(2):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            # First response: rate limit, second response: success
            mock_responses = [
                Mock(status_code=429, json=Mock(return_value={"parameters": {"retry_after": 1}})),
                Mock(status_code=200, json=Mock(return_value={"ok": True, "result": [{"message_id": 123}]}))
            ]
            
            with patch.object(service._client, 'post', side_effect=mock_responses), \
                 patch('asyncio.sleep') as mock_sleep:
                
                result = await service.send_media_group("test_chat", tmp_files)
                
                assert result["ok"] is True
                mock_sleep.assert_called_once_with(2)  # retry_after + 1
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)
    
    @pytest.mark.asyncio
    async def test_send_media_group_file_not_found_during_send(self):
        """Test media group sending with file not found during send"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(2):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            # Delete one file after creation but before sending
            os.unlink(tmp_files[0])
            
            with pytest.raises(ValidationException) as exc_info:
                await service.send_media_group("test_chat", tmp_files)
            
            assert "Photo file not found" in str(exc_info.value)
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)
    
    @pytest.mark.asyncio
    async def test_send_media_group_request_error(self):
        """Test media group sending with request error"""
        service = TelegramService(bot_token="test_token")
        
        # Create temporary files
        tmp_files = []
        try:
            for i in range(2):
                tmp_file = tempfile.NamedTemporaryFile(suffix=f'.jpg', delete=False)
                tmp_file.write(b"fake image data")
                tmp_file.close()
                tmp_files.append(tmp_file.name)
            
            with patch.object(service._client, 'post', side_effect=httpx.RequestError("Connection failed")):
                with pytest.raises(ExternalServiceException) as exc_info:
                    await service.send_media_group("test_chat", tmp_files)
                
                assert "Network error" in str(exc_info.value)
                assert exc_info.value.details["operation"] == "send_media_group"
        finally:
            for tmp_file in tmp_files:
                if os.path.exists(tmp_file):
                    safe_unlink(tmp_file)


class TestTelegramServiceGetChatInfo:
    """Test get_chat_info method"""
    
    @pytest.mark.asyncio
    async def test_get_chat_info_disabled_service(self):
        """Test get_chat_info with disabled service"""
        service = TelegramService(bot_token=None)
        
        with pytest.raises(ValidationException) as exc_info:
            await service.get_chat_info("test_chat")
        
        assert "Telegram service is disabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_chat_info_success(self):
        """Test successful chat info retrieval"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {
                "id": -123456789,
                "title": "Test Channel",
                "type": "channel"
            }
        }
        
        with patch.object(service._client, 'post', return_value=mock_response):
            result = await service.get_chat_info("test_chat")
            
            assert result["ok"] is True
            assert result["result"]["title"] == "Test Channel"
    
    @pytest.mark.asyncio
    async def test_get_chat_info_api_error(self):
        """Test chat info retrieval with API error"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "error_code": 400,
            "description": "Chat not found"
        }
        
        with patch.object(service._client, 'post', return_value=mock_response):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.get_chat_info("test_chat")
            
            assert "Chat not found" in str(exc_info.value)
            assert exc_info.value.details["error_code"] == 400
    
    @pytest.mark.asyncio
    async def test_get_chat_info_http_error(self):
        """Test chat info retrieval with HTTP error"""
        service = TelegramService(bot_token="test_token")
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        with patch.object(service._client, 'post', return_value=mock_response):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.get_chat_info("test_chat")
            
            assert exc_info.value.details["status_code"] == 404
    
    @pytest.mark.asyncio
    async def test_get_chat_info_request_error(self):
        """Test chat info retrieval with request error"""
        service = TelegramService(bot_token="test_token")
        
        with patch.object(service._client, 'post', side_effect=httpx.RequestError("Connection failed")):
            with pytest.raises(ExternalServiceException) as exc_info:
                await service.get_chat_info("test_chat")
            
            assert "Network error" in str(exc_info.value)
            assert exc_info.value.details["operation"] == "get_chat_info"


class TestTelegramServiceDiagnoseChat:
    """Test diagnose_chat method"""
    
    @pytest.mark.asyncio
    async def test_diagnose_chat_disabled_service(self):
        """Test diagnose_chat with disabled service"""
        service = TelegramService(bot_token=None)
        
        result = await service.diagnose_chat("test_chat")
        
        assert result["accessible"] is False
        assert result["reason"] == "service_disabled"
        assert "service is disabled" in result["details"]
    
    @pytest.mark.asyncio
    async def test_diagnose_chat_success(self):
        """Test successful chat diagnosis"""
        service = TelegramService(bot_token="test_token")
        
        mock_chat_info = {
            "ok": True,
            "result": {
                "id": -123456789,
                "title": "Test Channel",
                "type": "channel",
                "username": "test_channel",
                "description": "This is a test channel with a long description that should be truncated after 100 characters to avoid excessive logging"
            }
        }
        
        with patch.object(service, 'get_chat_info', return_value=mock_chat_info):
            result = await service.diagnose_chat("test_chat")
            
            assert result["accessible"] is True
            assert result["chat_info"]["title"] == "Test Channel"
            assert result["chat_info"]["type"] == "channel"
            assert len(result["chat_info"]["description"]) == 100  # Truncated
    
    @pytest.mark.asyncio
    async def test_diagnose_chat_api_error(self):
        """Test chat diagnosis with API error response"""
        service = TelegramService(bot_token="test_token")
        
        mock_chat_info = {
            "ok": False,
            "error_code": 400,
            "description": "Chat not found"
        }
        
        with patch.object(service, 'get_chat_info', return_value=mock_chat_info):
            result = await service.diagnose_chat("test_chat")
            
            assert result["accessible"] is False
            assert result["reason"] == "api_error"
            assert result["details"] == "Chat not found"
            assert result["error_code"] == 400
    
    @pytest.mark.asyncio
    async def test_diagnose_chat_external_service_exception(self):
        """Test chat diagnosis with external service exception"""
        service = TelegramService(bot_token="test_token")
        
        exception = ExternalServiceException(
            service="telegram",
            message="API error",
            details={
                "telegram_response": {
                    "error_code": 403,
                    "description": "Forbidden"
                }
            }
        )
        
        with patch.object(service, 'get_chat_info', side_effect=exception):
            result = await service.diagnose_chat("test_chat")
            
            assert result["accessible"] is False
            assert result["reason"] == "telegram_api_error"
            assert result["error_code"] == 403
            assert result["description"] == "Forbidden"
    
    @pytest.mark.asyncio
    async def test_diagnose_chat_unexpected_exception(self):
        """Test chat diagnosis with unexpected exception"""
        service = TelegramService(bot_token="test_token")
        
        with patch.object(service, 'get_chat_info', side_effect=Exception("Unexpected error")):
            result = await service.diagnose_chat("test_chat")
            
            assert result["accessible"] is False
            assert result["reason"] == "unexpected_error"
            assert result["details"] == "Unexpected error"


class TestTelegramServiceUtilityMethods:
    """Test utility methods"""
    
    def test_is_enabled_true(self):
        """Test is_enabled with enabled service"""
        service = TelegramService(bot_token="test_token")
        assert service.is_enabled() is True
    
    def test_is_enabled_false(self):
        """Test is_enabled with disabled service"""
        service = TelegramService(bot_token=None)
        assert service.is_enabled() is False
    
    @pytest.mark.asyncio
    async def test_close_with_client(self):
        """Test close method with client"""
        service = TelegramService(bot_token="test_token")
        
        with patch.object(service._client, 'aclose') as mock_close:
            await service.close()
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test close method without client"""
        service = TelegramService(bot_token=None)
        
        # Should not raise exception
        await service.close()
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager"""
        service = TelegramService(bot_token="test_token")
        
        with patch.object(service, 'close') as mock_close:
            async with service as ctx_service:
                assert ctx_service is service
            
            mock_close.assert_called_once()


class TestTelegramServiceGlobalInstance:
    """Test global service instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert telegram_service is not None
        assert isinstance(telegram_service, TelegramService)
    
    def test_global_instance_uses_env_token(self):
        """Test global instance uses environment token"""
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "global_token"}):
            # Re-import to get fresh instance
            import importlib
            import services.telegram_service
            importlib.reload(services.telegram_service)
            
            assert services.telegram_service.telegram_service.bot_token == "global_token"
            assert services.telegram_service.telegram_service.enabled is True