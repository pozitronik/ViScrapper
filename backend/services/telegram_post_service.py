"""
Service for posting products to Telegram channels with template rendering
"""

import os
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from models.product import Product, TelegramChannel, TelegramPost
from schemas.telegram import TelegramPostCreate, PostStatus
from services.telegram_service import telegram_service
from services.template_service import template_renderer
from crud.telegram import create_post, update_post_status, get_channel_by_id
from crud.template import get_template_by_id
from crud.product import get_product_by_id
from utils.logger import get_logger
from exceptions.base import ValidationException

logger = get_logger(__name__)


class TelegramPostService:
    """Service for posting products to Telegram channels"""
    
    def __init__(self):
        """Initialize the telegram post service"""
        self.telegram_service = telegram_service
        self.template_renderer = template_renderer
        logger.info("Telegram post service initialized")
    
    async def preview_post(
        self,
        db: Session,
        product_id: int,
        channel_id: Optional[int] = None,
        template_id: Optional[int] = None,
        template_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Preview how a product post will look
        
        Args:
            db: Database session
            product_id: Product to preview
            channel_id: Channel to use for settings (optional)
            template_id: Template to use (optional)
            template_content: Custom template content (optional)
        
        Returns:
            Preview data including rendered content
            
        Raises:
            ValidationException: If product not found or template invalid
        """
        logger.info(f"Previewing post for product {product_id}")
        
        # Get product
        product = get_product_by_id(db, product_id)
        if not product:
            raise ValidationException(
                message="Product not found",
                details={"product_id": product_id}
            )
        
        # Get channel if provided
        channel = None
        if channel_id:
            channel = get_channel_by_id(db, channel_id)
            if not channel:
                raise ValidationException(
                    message="Channel not found",
                    details={"channel_id": channel_id}
                )
        
        # Determine template to use
        template_to_use = None
        if template_content:
            # Custom template content provided
            template_to_use = template_content
        elif template_id:
            # Specific template ID provided
            template = get_template_by_id(db, template_id)
            if not template:
                raise ValidationException(
                    message="Template not found",
                    details={"template_id": template_id}
                )
            template_to_use = template.template_content
        elif channel and channel.template_id:
            # Use channel's default template
            template = get_template_by_id(db, channel.template_id)
            if template:
                template_to_use = template.template_content
        
        # Fall back to default template if none found
        if not template_to_use:
            template_to_use = "📦 New Product: {product_name}\n💰 Price: {product_price} {product_currency}\n🔗 {product_url}"
        
        # Render the template
        try:
            rendered_content = self.template_renderer.render_template(template_to_use, product)
        except Exception as e:
            raise ValidationException(
                message="Template rendering failed",
                details={"template_content": template_to_use, "error": str(e)},
                original_exception=e
            )
        
        # Count photos
        photo_count = len([img for img in product.images if not img.deleted_at])
        
        # Determine if photos will be sent
        will_send_photos = True
        if channel:
            will_send_photos = channel.send_photos
        
        return {
            "rendered_content": rendered_content,
            "template_used": template_to_use,
            "product_name": product.name,
            "channel_name": channel.name if channel else None,
            "will_send_photos": will_send_photos,
            "photo_count": photo_count
        }
    
    async def send_post(
        self,
        db: Session,
        product_id: int,
        channel_ids: List[int],
        template_id: Optional[int] = None,
        template_content: Optional[str] = None,
        send_photos: Optional[bool] = None,
        disable_notification: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Send a product post to multiple telegram channels
        
        Args:
            db: Database session
            product_id: Product to post
            channel_ids: List of channel IDs to post to
            template_id: Template to use (optional)
            template_content: Custom template content (optional)
            send_photos: Override channel photo setting (optional)
            disable_notification: Override notification setting (optional)
        
        Returns:
            Results including created posts and any errors
            
        Raises:
            ValidationException: If product not found or telegram service disabled
        """
        if not self.telegram_service.is_enabled():
            raise ValidationException(
                message="Telegram service is disabled - bot token not configured",
                details={"telegram_enabled": False}
            )
        
        logger.info(f"Sending post for product {product_id} to {len(channel_ids)} channels")
        
        # Get product
        product = get_product_by_id(db, product_id)
        if not product:
            raise ValidationException(
                message="Product not found",
                details={"product_id": product_id}
            )
        
        posts_created = []
        errors = []
        success_count = 0
        failed_count = 0
        
        # Process each channel
        for channel_id in channel_ids:
            try:
                # Get channel
                channel = get_channel_by_id(db, channel_id)
                if not channel:
                    error_msg = f"Channel {channel_id} not found"
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                if not channel.is_active:
                    error_msg = f"Channel {channel.name} is not active"
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                # Determine template to use
                template_to_use = None
                template_id_used = None
                
                if template_content:
                    template_to_use = template_content
                elif template_id:
                    template = get_template_by_id(db, template_id)
                    if template:
                        template_to_use = template.template_content
                        template_id_used = template_id
                elif channel.template_id:
                    template = get_template_by_id(db, channel.template_id)
                    if template:
                        template_to_use = template.template_content
                        template_id_used = channel.template_id
                
                if not template_to_use:
                    template_to_use = "📦 New Product: {product_name}\n💰 Price: {product_price} {product_currency}\n🔗 {product_url}"
                
                # Render the template
                try:
                    rendered_content = self.template_renderer.render_template(template_to_use, product)
                except Exception as e:
                    error_msg = f"Template rendering failed for channel {channel.name}: {str(e)}"
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                # Create post record
                post_data = TelegramPostCreate(
                    product_id=product_id,
                    channel_id=channel_id,
                    template_id=template_id_used
                )
                
                db_post = create_post(db, post_data, rendered_content)
                db.commit()  # Commit the post creation
                
                # Send to telegram
                await self._send_post_to_telegram(db, db_post, channel, product, send_photos, disable_notification)
                
                posts_created.append(db_post)
                success_count += 1
                
            except Exception as e:
                error_msg = f"Failed to send to channel {channel_id}: {str(e)}"
                errors.append(error_msg)
                failed_count += 1
                logger.error(f"Error sending post to channel {channel_id}: {e}")
                continue
        
        return {
            "posts_created": posts_created,
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def _send_post_to_telegram(
        self,
        db: Session,
        post: TelegramPost,
        channel: TelegramChannel,
        product: Product,
        send_photos_override: Optional[bool] = None,
        disable_notification_override: Optional[bool] = None
    ):
        """
        Send a single post to telegram
        
        Args:
            db: Database session
            post: TelegramPost record
            channel: TelegramChannel to send to
            product: Product being posted
            send_photos_override: Override channel photo setting
            disable_notification_override: Override notification setting
        """
        try:
            # Determine settings
            should_send_photos = send_photos_override if send_photos_override is not None else channel.send_photos
            should_disable_notification = disable_notification_override if disable_notification_override is not None else channel.disable_notification
            
            # Get product photos if needed
            photo_paths = []
            if should_send_photos:
                active_images = [img for img in product.images if not img.deleted_at]
                for image in active_images:
                    # Image URL should be the local file ID from image downloader
                    image_path = os.path.join("images", f"{image.url}.jpg")
                    if os.path.exists(image_path):
                        photo_paths.append(image_path)
            
            # Send message to telegram
            if photo_paths:
                if len(photo_paths) == 1:
                    # Send single photo with caption
                    result = await self.telegram_service.send_photo(
                        chat_id=channel.chat_id,
                        photo_path=photo_paths[0],
                        caption=post.rendered_content,
                        parse_mode="HTML",
                        disable_notification=should_disable_notification
                    )
                else:
                    # Send media group with caption on first photo
                    result = await self.telegram_service.send_media_group(
                        chat_id=channel.chat_id,
                        media_paths=photo_paths,
                        caption=post.rendered_content,
                        parse_mode="HTML",
                        disable_notification=should_disable_notification
                    )
            else:
                # Send text message only
                result = await self.telegram_service.send_message(
                    chat_id=channel.chat_id,
                    text=post.rendered_content,
                    parse_mode="HTML",
                    disable_web_page_preview=channel.disable_web_page_preview,
                    disable_notification=should_disable_notification
                )
            
            # Extract message ID from result
            message_id = None
            if result and result.get("ok") and result.get("result"):
                if isinstance(result["result"], list):
                    # Media group returns list of messages
                    message_id = result["result"][0].get("message_id")
                else:
                    # Single message
                    message_id = result["result"].get("message_id")
            
            # Update post as sent
            update_post_status(db, post.id, PostStatus.SENT, message_id=message_id)
            db.commit()
            
            logger.info(f"Successfully sent post {post.id} to channel {channel.name}")
            
        except Exception as e:
            # Update post as failed
            error_message = str(e)
            update_post_status(db, post.id, PostStatus.FAILED, error_message=error_message)
            db.commit()
            
            logger.error(f"Failed to send post {post.id} to channel {channel.name}: {e}")
            raise
    
    async def retry_failed_posts(self, db: Session, max_retries: int = 3) -> Dict[str, Any]:
        """
        Retry failed telegram posts
        
        Args:
            db: Database session
            max_retries: Maximum retry attempts
        
        Returns:
            Results of retry attempts
        """
        logger.info("Retrying failed telegram posts")
        
        # Get failed posts that haven't exceeded max retries
        failed_posts = db.query(TelegramPost).filter(
            TelegramPost.status == PostStatus.FAILED.value,
            TelegramPost.retry_count < max_retries
        ).all()
        
        if not failed_posts:
            logger.info("No failed posts to retry")
            return {"retried_count": 0, "success_count": 0, "failed_count": 0, "errors": []}
        
        logger.info(f"Found {len(failed_posts)} failed posts to retry")
        
        success_count = 0
        failed_count = 0
        errors = []
        
        for post in failed_posts:
            try:
                # Get related objects
                channel = get_channel_by_id(db, post.channel_id)
                product = get_product_by_id(db, post.product_id)
                
                if not channel or not product:
                    error_msg = f"Post {post.id}: Missing channel or product"
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                if not channel.is_active:
                    error_msg = f"Post {post.id}: Channel {channel.name} is not active"
                    errors.append(error_msg)
                    failed_count += 1
                    continue
                
                # Retry sending
                await self._send_post_to_telegram(db, post, channel, product)
                success_count += 1
                
            except Exception as e:
                error_msg = f"Post {post.id}: Retry failed - {str(e)}"
                errors.append(error_msg)
                failed_count += 1
                logger.error(f"Failed to retry post {post.id}: {e}")
        
        return {
            "retried_count": len(failed_posts),
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
    
    async def auto_post_product(self, db: Session, product_id: int) -> Dict[str, Any]:
        """
        Auto-post a product to channels with auto_post enabled
        
        Args:
            db: Database session
            product_id: Product to auto-post
        
        Returns:
            Results of auto-posting
        """
        logger.info(f"Auto-posting product {product_id}")
        
        # Get channels with auto_post enabled
        auto_post_channels = db.query(TelegramChannel).filter(
            TelegramChannel.auto_post == True,
            TelegramChannel.is_active == True,
            TelegramChannel.deleted_at.is_(None)
        ).all()
        
        if not auto_post_channels:
            logger.info("No auto-post channels configured")
            return {"success_count": 0, "failed_count": 0, "errors": []}
        
        channel_ids = [channel.id for channel in auto_post_channels]
        
        return await self.send_post(
            db=db,
            product_id=product_id,
            channel_ids=channel_ids
        )


# Global instance
telegram_post_service = TelegramPostService()