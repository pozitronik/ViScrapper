"""
Telegram service for sending messages and media
"""
import httpx
from typing import List, Optional, Dict, Any
import os
import json
import asyncio
import time

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

    async def _handle_rate_limit_retry(self, response: httpx.Response, operation: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Handle HTTP 429 rate limiting with retry logic
        
        Args:
            response: The HTTP response that returned 429
            operation: Description of the operation being retried
            max_retries: Maximum number of retry attempts
            
        Returns:
            None if should continue with normal error handling, or retry result if successful
        """
        if response.status_code != 429:
            return None
            
        try:
            error_data = response.json()
            retry_after = error_data.get("parameters", {}).get("retry_after", 5)
            
            logger.warning(f"Rate limit hit for {operation}. Telegram API requests retry after {retry_after} seconds.")
            
            # Wait the specified time plus a small buffer
            await asyncio.sleep(retry_after + 1)
            
            logger.info(f"Retrying {operation} after rate limit delay...")
            return {"retry": True, "retry_after": retry_after}
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse rate limit response for {operation}: {e}")
            return None

    async def send_message(
            self,
            chat_id: str,
            text: str,
            parse_mode: str = "HTML",
            disable_web_page_preview: bool = True,
            disable_notification: bool = False,
            reply_to_message_id: Optional[int] = None,
            max_retries: int = 3
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
            max_retries: Maximum number of retry attempts for rate limiting
        
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

        logger.info(f"Sending message to chat {chat_id} (text length: {len(text)})")

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

        logger.debug(f"Request data for chat {chat_id}: {data}")
        logger.info(f"Full request URL: {self.base_url}/sendMessage")
        logger.info(f"Chat ID type: {type(chat_id)}, value: '{chat_id}'")

        try:
            retry_count = 0
            while retry_count <= max_retries:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    logger.debug(f"Making POST request to: {self.base_url}/sendMessage")
                    response = await client.post(
                        f"{self.base_url}/sendMessage",
                        data=data
                    )

                    logger.debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.debug(f"Response JSON: {result}")
                        if isinstance(result, dict) and result.get("ok"):
                            logger.info(f"Message sent successfully to {chat_id}")
                            if retry_count > 0:
                                logger.info(f"Success after {retry_count} retries due to rate limiting")
                            return result
                        else:
                            error_code = result.get("error_code", "unknown")
                            error_description = result.get("description", "Unknown error")
                            logger.error(f"Telegram API error for chat {chat_id}: Code {error_code}, Description: {error_description}, Full response: {result}")
                            raise ExternalServiceException(
                                service="telegram",
                                message=f"Telegram API error: {error_description}",
                                details={
                                    "telegram_response": result, 
                                    "chat_id": chat_id, 
                                    "operation": "send_message",
                                    "error_code": error_code,
                                    "bot_token_present": bool(self.bot_token),
                                    "request_data": {k: v for k, v in data.items() if k != "text"}  # Exclude text for privacy
                                }
                            )
                    else:
                        # Check if this is a rate limit error (429)
                        if response.status_code == 429 and retry_count < max_retries:
                            retry_result = await self._handle_rate_limit_retry(response, "send_message")
                            if retry_result and retry_result.get("retry"):
                                retry_count += 1
                                logger.info(f"Rate limit retry {retry_count}/{max_retries} for message to {chat_id}")
                                continue
                        
                        response_text = response.text
                        logger.error(f"HTTP error {response.status_code} for chat {chat_id}: {response_text}")
                        
                        # Try to parse JSON error response
                        try:
                            error_json = response.json()
                            logger.error(f"Parsed error response: {error_json}")
                        except Exception:
                            logger.error("Could not parse error response as JSON")
                        
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"HTTP error {response.status_code}",
                            details={
                                "status_code": response.status_code, 
                                "response": response_text, 
                                "operation": "send_message",
                                "chat_id": chat_id,
                                "bot_token_present": bool(self.bot_token),
                                "retry_count": retry_count
                            }
                        )
                        
            # If we get here, we've exhausted all retries
            logger.error(f"Exhausted all {max_retries} retries for message to {chat_id}")
            raise ExternalServiceException(
                service="telegram",
                message=f"Failed to send message after {max_retries} retries due to rate limiting",
                details={
                    "status_code": 429,
                    "operation": "send_message",
                    "chat_id": chat_id,
                    "retry_count": retry_count
                }
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
            disable_notification: bool = False,
            max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Send a photo to a Telegram chat
        
        Args:
            chat_id: Telegram chat ID
            photo_path: Local path to photo file
            caption: Photo caption (up to 1024 characters)
            parse_mode: Caption formatting
            disable_notification: Send silently
            max_retries: Maximum number of retry attempts for rate limiting
        
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

            retry_count = 0
            with open(photo_path, "rb") as photo_file:
                files = {"photo": photo_file}

                while retry_count <= max_retries:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{self.base_url}/sendPhoto",
                            data=data,
                            files=files
                        )

                        if response.status_code == 200:
                            result = response.json()
                            if isinstance(result, dict) and result.get("ok"):
                                logger.info(f"Photo sent successfully to {chat_id}")
                                if retry_count > 0:
                                    logger.info(f"Success after {retry_count} retries due to rate limiting")
                                return result
                            else:
                                logger.error(f"Telegram API error: {result}")
                                raise ExternalServiceException(
                                    service="telegram",
                                    message=f"Telegram API error: {result.get('description', 'Unknown error')}",
                                    details={"telegram_response": result, "chat_id": chat_id, "operation": "send_photo"}
                                )
                        else:
                            # Check if this is a rate limit error (429)
                            if response.status_code == 429 and retry_count < max_retries:
                                retry_result = await self._handle_rate_limit_retry(response, "send_photo")
                                if retry_result and retry_result.get("retry"):
                                    retry_count += 1
                                    logger.info(f"Rate limit retry {retry_count}/{max_retries} for photo to {chat_id}")
                                    # Reset file pointer to beginning for retry
                                    photo_file.seek(0)
                                    continue
                            
                            logger.error(f"HTTP error {response.status_code}: {response.text}")
                            raise ExternalServiceException(
                                service="telegram",
                                message=f"HTTP error {response.status_code}",
                                details={
                                    "status_code": response.status_code, 
                                    "response": response.text, 
                                    "operation": "send_photo",
                                    "retry_count": retry_count
                                }
                            )
                            
                # If we get here, we've exhausted all retries
                logger.error(f"Exhausted all {max_retries} retries for photo to {chat_id}")
                raise ExternalServiceException(
                    service="telegram",
                    message=f"Failed to send photo after {max_retries} retries due to rate limiting",
                    details={
                        "status_code": 429,
                        "operation": "send_photo",
                        "chat_id": chat_id,
                        "retry_count": retry_count
                    }
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
            disable_notification: bool = False,
            max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Send multiple photos as a media group
        
        Args:
            chat_id: Telegram chat ID
            media_paths: List of local photo paths (2-10 items)
            caption: Caption for the first photo
            parse_mode: Caption formatting
            disable_notification: Send silently
            max_retries: Maximum number of retry attempts for rate limiting
        
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

        # Properly serialize media to JSON
        media_json = json.dumps(media)
        logger.debug(f"Media JSON for chat {chat_id}: {media_json}")

        data = {
            "chat_id": chat_id,
            "media": media_json,
            "disable_notification": disable_notification
        }

        # Prepare files inside try block to ensure cleanup
        files = {}
        retry_count = 0
        
        try:
            # Open files
            for i, path in enumerate(media_paths):
                files[f"photo{i}"] = open(path, "rb")

            while retry_count <= max_retries:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/sendMediaGroup",
                        data=data,
                        files=files
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if isinstance(result, dict) and result.get("ok"):
                            logger.info(f"Media group sent successfully to {chat_id}")
                            if retry_count > 0:
                                logger.info(f"Success after {retry_count} retries due to rate limiting")
                            return result
                        else:
                            error_code = result.get("error_code", "unknown")
                            error_description = result.get("description", "Unknown error")
                            logger.error(f"Telegram API error for media group to {chat_id}: Code {error_code}, Description: {error_description}, Full response: {result}")
                            raise ExternalServiceException(
                                service="telegram",
                                message=f"Telegram API error: {error_description}",
                                details={
                                    "telegram_response": result, 
                                    "chat_id": chat_id, 
                                    "operation": "send_media_group",
                                    "error_code": error_code,
                                    "media_count": len(media_paths),
                                    "media_json": media_json
                                }
                            )
                    else:
                        # Check if this is a rate limit error (429)
                        if response.status_code == 429 and retry_count < max_retries:
                            retry_result = await self._handle_rate_limit_retry(response, "send_media_group")
                            if retry_result and retry_result.get("retry"):
                                retry_count += 1
                                logger.info(f"Rate limit retry {retry_count}/{max_retries} for media group to {chat_id}")
                                # Reset file pointers to beginning for retry
                                for file_obj in files.values():
                                    file_obj.seek(0)
                                continue
                        
                        response_text = response.text
                        logger.error(f"HTTP error {response.status_code} for media group to {chat_id}: {response_text}")
                        
                        # Try to parse JSON error response
                        try:
                            error_json = response.json()
                            logger.error(f"Parsed media group error response: {error_json}")
                        except Exception:
                            logger.error("Could not parse media group error response as JSON")
                        
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"HTTP error {response.status_code}",
                            details={
                                "status_code": response.status_code, 
                                "response": response_text, 
                                "operation": "send_media_group",
                                "chat_id": chat_id,
                                "media_count": len(media_paths),
                                "retry_count": retry_count
                            }
                        )
                        
                # If we get here, we've exhausted all retries
                logger.error(f"Exhausted all {max_retries} retries for media group to {chat_id}")
                raise ExternalServiceException(
                    service="telegram",
                    message=f"Failed to send media group after {max_retries} retries due to rate limiting",
                    details={
                        "status_code": 429,
                        "operation": "send_media_group",
                        "chat_id": chat_id,
                        "media_count": len(media_paths),
                        "retry_count": retry_count
                    }
                )
        except FileNotFoundError as e:
            raise ValidationException(
                message="Photo file not found during media group upload",
                details={"missing_file": str(e)}
            )
        except httpx.RequestError as e:
            logger.error(f"Request error sending media group to Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "media_count": len(media_paths), "operation": "send_media_group"}
            )
        finally:
            # Close all opened files (only those that were successfully opened)
            for file_obj in files.values():
                file_obj.close()

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
        logger.debug(f"Chat ID type: {type(chat_id)}, value: {chat_id}")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.debug(f"Making POST request to: {self.base_url}/getChat")
                response = await client.post(
                    f"{self.base_url}/getChat",
                    data={"chat_id": chat_id}
                )

                logger.debug(f"Response status for getChat: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    logger.debug(f"getChat response JSON: {result}")
                    if isinstance(result, dict) and result.get("ok"):
                        logger.info(f"Chat info retrieved for {chat_id}: {result.get('result', {}).get('title', 'N/A')}")
                        return result
                    else:
                        error_code = result.get("error_code", "unknown")
                        error_description = result.get("description", "Unknown error")
                        logger.error(f"Telegram API error for getChat {chat_id}: Code {error_code}, Description: {error_description}, Full response: {result}")
                        raise ExternalServiceException(
                            service="telegram",
                            message=f"Telegram API error: {error_description}",
                            details={
                                "telegram_response": result, 
                                "chat_id": chat_id, 
                                "operation": "get_chat_info",
                                "error_code": error_code,
                                "bot_token_present": bool(self.bot_token)
                            }
                        )
                else:
                    response_text = response.text
                    logger.error(f"HTTP error {response.status_code} for getChat {chat_id}: {response_text}")
                    
                    # Try to parse JSON error response
                    try:
                        error_json = response.json()
                        logger.error(f"Parsed getChat error response: {error_json}")
                    except Exception:
                        logger.error("Could not parse getChat error response as JSON")
                    
                    raise ExternalServiceException(
                        service="telegram",
                        message=f"HTTP error {response.status_code}",
                        details={
                            "status_code": response.status_code, 
                            "response": response_text, 
                            "operation": "get_chat_info",
                            "chat_id": chat_id,
                            "bot_token_present": bool(self.bot_token)
                        }
                    )

        except httpx.RequestError as e:
            logger.error(f"Request error getting chat info from Telegram: {e}")
            raise ExternalServiceException(
                service="telegram",
                message="Network error communicating with Telegram",
                original_exception=e,
                details={"chat_id": chat_id, "operation": "get_chat_info"}
            )

    async def diagnose_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Diagnose chat accessibility and provide detailed information
        
        Args:
            chat_id: Telegram chat ID to diagnose
        
        Returns:
            Diagnostic information about the chat
        """
        if not self.enabled:
            return {
                "accessible": False,
                "reason": "service_disabled",
                "details": "Telegram service is disabled - bot token not configured"
            }

        logger.info(f"Diagnosing chat {chat_id}")
        
        try:
            # Try to get chat info first
            chat_info = await self.get_chat_info(chat_id)
            
            if chat_info.get("ok"):
                chat_result = chat_info.get("result", {})
                return {
                    "accessible": True,
                    "chat_info": {
                        "id": chat_result.get("id"),
                        "title": chat_result.get("title"),
                        "type": chat_result.get("type"),
                        "username": chat_result.get("username"),
                        "description": chat_result.get("description", "")[:100]  # First 100 chars
                    },
                    "details": "Chat is accessible"
                }
            else:
                return {
                    "accessible": False,
                    "reason": "api_error",
                    "details": chat_info.get("description", "Unknown API error"),
                    "error_code": chat_info.get("error_code")
                }
                
        except ExternalServiceException as e:
            error_details = e.details or {}
            telegram_response = error_details.get("telegram_response", {})
            
            return {
                "accessible": False,
                "reason": "telegram_api_error",
                "details": str(e),
                "error_code": telegram_response.get("error_code"),
                "description": telegram_response.get("description"),
                "full_error": telegram_response
            }
            
        except Exception as e:
            logger.error(f"Unexpected error diagnosing chat {chat_id}: {e}")
            return {
                "accessible": False,
                "reason": "unexpected_error",
                "details": str(e)
            }

    def is_enabled(self) -> bool:
        """Check if Telegram service is enabled"""
        return self.enabled


# Global instance
telegram_service = TelegramService()
