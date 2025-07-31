"""
Service for posting products to Telegram channels with template rendering
"""

import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from models.product import Product, TelegramChannel, TelegramPost
from schemas.telegram import TelegramPostCreate, PostStatus
from services.telegram_service import telegram_service
from services.template_service import template_renderer
from services.image_combination_service import combine_product_images
from services.image_optimization_service import optimize_product_image
from crud.telegram import create_post, update_post_status, get_channel_by_id
from crud.template import get_template_by_id
from crud.product import get_product_by_id
from utils.logger import get_logger
from exceptions.base import ValidationException

logger = get_logger(__name__)


class TelegramPostService:
    """Service for posting products to Telegram channels"""

    def __init__(self) -> None:
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
    ) -> None:
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
                    # Image URL in database is the filename (UUID.jpg)
                    if image.url:
                        image_path = os.path.join("images", image.url)
                        if os.path.exists(image_path):
                            photo_paths.append(image_path)
                        else:
                            logger.warning(f"Image file not found: {image_path}")
                            # Try alternative path without extension
                            alt_path = os.path.join("images", f"{image.url}.jpg")
                            if os.path.exists(alt_path):
                                photo_paths.append(alt_path)
                            else:
                                logger.warning(f"Alternative image path also not found: {alt_path}")

                # Apply image processing based on template settings
                if photo_paths:
                    photo_paths = await self._process_images_for_template(db, post, photo_paths)

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

            # Update product's telegram_posted_at timestamp
            product.telegram_posted_at = datetime.now(timezone.utc)
            db.add(product)
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

    async def _process_images_for_template(
        self,
        db: Session,
        post: TelegramPost,
        original_image_paths: List[str]
    ) -> List[str]:
        """
        Process images based on template settings (combination and optimization).
        
        Args:
            db: Database session
            post: TelegramPost containing template information
            original_image_paths: List of original image file paths
            
        Returns:
            List of processed image file paths
        """
        try:
            # Get template to check for image processing settings
            template = None
            if post.template_id:
                template = get_template_by_id(db, post.template_id)
            
            # If no template or no image processing needed, return original paths
            if not template or (not template.combine_images and not template.optimize_images):
                logger.debug("No image processing needed - using original images")
                return original_image_paths
            
            processed_paths = []
            
            # Step 1: Combine images if requested
            if template.combine_images and len(original_image_paths) > 1:
                logger.info(f"Combining {len(original_image_paths)} images for template '{template.name}'")
                try:
                    combined_images_bytes = await combine_product_images(
                        image_paths=original_image_paths,
                        max_width=template.max_width,
                        max_height=template.max_height,
                        spacing=10  # Fixed spacing for now
                    )
                    
                    # Save all combined images
                    processed_paths = []
                    for i, image_bytes in enumerate(combined_images_bytes):
                        combined_filename = f"combined_{uuid.uuid4()}.jpg"
                        combined_path = os.path.join("images", combined_filename)
                        
                        with open(combined_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        processed_paths.append(combined_path)
                    
                    logger.info(f"Images combined successfully: {len(processed_paths)} combined images created")
                    
                except Exception as e:
                    logger.error(f"Image combination failed: {e}. Using original images.")
                    processed_paths = original_image_paths
            else:
                processed_paths = original_image_paths
            
            # Step 2: Optimize images if requested
            if template.optimize_images:
                logger.info(f"Optimizing {len(processed_paths)} images for template '{template.name}'")
                optimized_paths = []
                
                for image_path in processed_paths:
                    try:
                        # Read original image
                        with open(image_path, 'rb') as f:
                            image_data = f.read()
                        
                        # Optimize image
                        optimized_data = await optimize_product_image(
                            image_data=image_data,
                            max_file_size_kb=template.max_file_size_kb,
                            max_width=template.max_width,
                            max_height=template.max_height,
                            compression_quality=template.compression_quality
                        )
                        
                        # Save optimized image
                        if image_path.startswith("combined_"):
                            # For combined images, replace the temporary file
                            optimized_path = image_path
                        else:
                            # For regular images, create new optimized file
                            base_name = os.path.splitext(os.path.basename(image_path))[0]
                            optimized_filename = f"opt_{base_name}_{uuid.uuid4().hex[:8]}.jpg"
                            optimized_path = os.path.join("images", optimized_filename)
                        
                        with open(optimized_path, 'wb') as f:
                            f.write(optimized_data)
                        
                        optimized_paths.append(optimized_path)
                        logger.debug(f"Image optimized: {image_path} -> {optimized_path}")
                        
                        # Clean up temporary combined file if it's different from optimized
                        if image_path != optimized_path and image_path.startswith("images/combined_"):
                            try:
                                os.remove(image_path)
                            except:
                                pass
                        
                    except Exception as e:
                        logger.error(f"Image optimization failed for {image_path}: {e}. Using original.")
                        optimized_paths.append(image_path)
                
                processed_paths = optimized_paths
            
            logger.info(f"Image processing completed. Final paths: {processed_paths}")
            return processed_paths
            
        except Exception as e:
            logger.error(f"Image processing failed: {e}. Using original images.")
            return original_image_paths


# Global instance
telegram_post_service = TelegramPostService()
