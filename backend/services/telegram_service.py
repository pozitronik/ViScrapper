"""
Telegram service for sending messages and media
"""
import httpx
from typing import List, Optional, Dict, Any
import os

from utils.logger import get_logger
from exceptions.base import ExternalServiceException, ValidationException

logger = get_logger(__name__)


class TelegramService:
    """Service for interacting with Telegram Bot API"""
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram service
        
        Args:
            bot_token: Telegram bot token. If None, reads from environment
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            logger.warning("Telegram bot token not provided. Service will be disabled.")
            self.enabled = False
        else:
            self.enabled = True
            self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
            logger.info("Telegram service initialized successfully")
    
    async def send_message(
        self, 
        chat_id: str, 
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = True,
        disable_notification: bool = False,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a text message to a Telegram chat
        
        Args:
            chat_id: Telegram chat ID (can be channel username with @)
            text: Message text (up to 4096 characters)
            parse_mode: Message formatting (HTML, Markdown, or None)
            disable_web_page_preview: Disable link previews
            disable_notification: Send message silently
            reply_to_message_id: Reply to specific message
        
        Returns:
            Telegram API response
            
        Raises:
            ValidationException: If service is disabled or parameters invalid
            ExternalServiceException: If Telegram API request fails
        """
        if not self.enabled:
            raise ValidationException(
                message="Telegram service is disabled - bot token not configured",
                details={"bot_token_configured": False}
            )
        
        if not chat_id:
            raise ValidationException(
                message="Chat ID is required",
                details={"chat_id": chat_id}
            )
        
        if not text or len(text) > 4096:
            raise ValidationException(
                message="Message text must be 1-4096 characters",
                details={"text_length": len(text) if text else 0}
            )
        
        logger.info(f"Sending message to chat {chat_id}")
        
        # Prepare request data
        data = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification
        }
        
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    data=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Message sent successfully to {chat_id}")
                        return result
                    else:
                        logger.error(f"Telegram API error: {result}")
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"Telegram API error: {result.get('description', 'Unknown error')}",
                            details={"telegram_response": result, "chat_id": chat_id, "operation": "send_message"}
                        )
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                    raise ExternalServiceException(
                        service="telegram",
                        message=f"HTTP error {response.status_code}",
                        details={"status_code": response.status_code, "response": response.text, "operation": "send_message"}
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Request error sending message to Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "operation": "send_message"}
            )
    
    async def send_photo(
        self,
        chat_id: str,
        photo_path: str,
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        Send a photo to a Telegram chat
        
        Args:
            chat_id: Telegram chat ID
            photo_path: Local path to photo file
            caption: Photo caption (up to 1024 characters)
            parse_mode: Caption formatting
            disable_notification: Send silently
        
        Returns:
            Telegram API response
            
        Raises:
            ValidationException: If parameters invalid or file not found
            ExternalServiceException: If Telegram API request fails
        """
        if not self.enabled:
            raise ValidationException(
                message="Telegram service is disabled - bot token not configured",
                details={"bot_token_configured": False}
            )
        
        if not os.path.exists(photo_path):
            raise ValidationException(
                message="Photo file not found",
                details={"photo_path": photo_path}
            )
        
        if caption and len(caption) > 1024:
            raise ValidationException(
                message="Photo caption must be up to 1024 characters",
                details={"caption_length": len(caption)}
            )
        
        logger.info(f"Sending photo to chat {chat_id}: {photo_path}")
        
        try:
            data = {
                "chat_id": chat_id,
                "disable_notification": disable_notification
            }
            
            if caption:
                data["caption"] = caption
                if parse_mode:
                    data["parse_mode"] = parse_mode
            
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/sendPhoto",
                        data=data,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Photo sent successfully to {chat_id}")
                            return result
                        else:
                            logger.error(f"Telegram API error: {result}")
                            raise ExternalServiceException(
                                service="telegram",
                                message=f"Telegram API error: {result.get('description', 'Unknown error')}",
                                details={"telegram_response": result, "chat_id": chat_id, "operation": "send_photo"}
                            )
                    else:
                        logger.error(f"HTTP error {response.status_code}: {response.text}")
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"HTTP error {response.status_code}",
                            details={"status_code": response.status_code, "response": response.text, "operation": "send_photo"}
                        )
                        
        except FileNotFoundError:
            raise ValidationException(
                message="Photo file not found",
                details={"photo_path": photo_path}
            )
        except httpx.RequestError as e:
            logger.error(f"Request error sending photo to Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "photo_path": photo_path, "operation": "send_photo"}
            )
    
    async def send_media_group(
        self,
        chat_id: str,
        media_paths: List[str],
        caption: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> Dict[str, Any]:
        """
        Send multiple photos as a media group
        
        Args:
            chat_id: Telegram chat ID
            media_paths: List of local photo paths (2-10 items)
            caption: Caption for the first photo
            parse_mode: Caption formatting
            disable_notification: Send silently
        
        Returns:
            Telegram API response
            
        Raises:
            ValidationException: If parameters invalid
            ExternalServiceException: If Telegram API request fails
        """
        if not self.enabled:
            raise ValidationException(
                message="Telegram service is disabled - bot token not configured",
                details={"bot_token_configured": False}
            )
        
        if not media_paths or len(media_paths) < 2 or len(media_paths) > 10:
            raise ValidationException(
                message="Media group must contain 2-10 photos",
                details={"media_count": len(media_paths) if media_paths else 0}
            )
        
        for path in media_paths:
            if not os.path.exists(path):
                raise ValidationException(
                    message="Photo file not found",
                    details={"photo_path": path}
                )
        
        logger.info(f"Sending media group to chat {chat_id}: {len(media_paths)} photos")
        
        try:
            # Prepare media array
            media = []
            for i, path in enumerate(media_paths):
                media_item = {
                    "type": "photo",
                    "media": f"attach://photo{i}"
                }
                
                # Add caption to first photo only
                if i == 0 and caption:
                    media_item["caption"] = caption
                    if parse_mode:
                        media_item["parse_mode"] = parse_mode
                
                media.append(media_item)
            
            data = {
                "chat_id": chat_id,
                "media": str(media).replace("'", '"'),  # Convert to JSON string
                "disable_notification": disable_notification
            }
            
            # Prepare files
            files = {}
            for i, path in enumerate(media_paths):
                files[f"photo{i}"] = open(path, "rb")
            
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/sendMediaGroup",
                        data=data,
                        files=files
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Media group sent successfully to {chat_id}")
                            return result
                        else:
                            logger.error(f"Telegram API error: {result}")
                            raise ExternalServiceException(
                                service="telegram",
                                message=f"Telegram API error: {result.get('description', 'Unknown error')}",
                                details={"telegram_response": result, "chat_id": chat_id, "operation": "send_media_group"}
                            )
                    else:
                        logger.error(f"HTTP error {response.status_code}: {response.text}")
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"HTTP error {response.status_code}",
                            details={"status_code": response.status_code, "response": response.text, "operation": "send_media_group"}
                        )
            finally:
                # Close all opened files
                for file_obj in files.values():
                    file_obj.close()
                    
        except httpx.RequestError as e:
            logger.error(f"Request error sending media group to Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "media_count": len(media_paths), "operation": "send_media_group"}
            )
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """
        Get information about a chat
        
        Args:
            chat_id: Telegram chat ID
        
        Returns:
            Chat information
            
        Raises:
            ValidationException: If service disabled
            ExternalServiceException: If API request fails
        """
        if not self.enabled:
            raise ValidationException(
                message="Telegram service is disabled - bot token not configured",
                details={"bot_token_configured": False}
            )
        
        logger.info(f"Getting chat info for {chat_id}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/getChat",
                    data={"chat_id": chat_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Chat info retrieved for {chat_id}")
                        return result
                    else:
                        logger.error(f"Telegram API error: {result}")
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"Telegram API error: {result.get('description', 'Unknown error')}",
                            details={"telegram_response": result, "chat_id": chat_id, "operation": "get_chat_info"}
                        )
                else:
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                    raise ExternalServiceException(
                        service="telegram",
                        message=f"HTTP error {response.status_code}",
                        details={"status_code": response.status_code, "response": response.text, "operation": "get_chat_info"}
                    )
                    
        except httpx.RequestError as e:
            logger.error(f"Request error getting chat info from Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "operation": "get_chat_info"}
            )
    
    def is_enabled(self) -> bool:
        """Check if Telegram service is enabled"""
        return self.enabled


# Global instance
telegram_service = TelegramService()