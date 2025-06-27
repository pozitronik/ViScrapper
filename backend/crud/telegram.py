"""
CRUD operations for Telegram channels and posts
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from models.product import TelegramChannel, TelegramPost, Product, MessageTemplate
from schemas.telegram import (
    TelegramChannelCreate, TelegramChannelUpdate, TelegramPostCreate,
    PostStatus
)
from utils.logger import get_logger
from utils.database import atomic_transaction
from exceptions.base import DatabaseException, ValidationException

logger = get_logger(__name__)


# Telegram Channel CRUD Operations

def get_channel_by_id(db: Session, channel_id: int, include_deleted: bool = False) -> Optional[TelegramChannel]:
    """Get telegram channel by ID"""
    logger.debug(f"Searching for telegram channel with ID: {channel_id}")
    
    try:
        query = db.query(TelegramChannel).filter(TelegramChannel.id == channel_id)
        
        if not include_deleted:
            query = query.filter(TelegramChannel.deleted_at.is_(None))
        
        channel = query.first()
        
        if channel:
            logger.debug(f"Found telegram channel: {channel.name}")
        else:
            logger.debug(f"No telegram channel found for ID: {channel_id}")
        
        return channel
        
    except Exception as e:
        logger.error(f"Error retrieving telegram channel by ID {channel_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve telegram channel by ID",
            operation="get_channel_by_id",
            table="telegram_channels",
            details={"channel_id": channel_id},
            original_exception=e
        )


def get_channel_by_chat_id(db: Session, chat_id: str, include_deleted: bool = False) -> Optional[TelegramChannel]:
    """Get telegram channel by chat ID"""
    logger.debug(f"Searching for telegram channel with chat_id: {chat_id}")
    
    try:
        query = db.query(TelegramChannel).filter(TelegramChannel.chat_id == chat_id)
        
        if not include_deleted:
            query = query.filter(TelegramChannel.deleted_at.is_(None))
        
        channel = query.first()
        
        if channel:
            logger.debug(f"Found telegram channel: {channel.name}")
        else:
            logger.debug(f"No telegram channel found for chat_id: {chat_id}")
        
        return channel
        
    except Exception as e:
        logger.error(f"Error retrieving telegram channel by chat_id {chat_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve telegram channel by chat_id",
            operation="get_channel_by_chat_id",
            table="telegram_channels",
            details={"chat_id": chat_id},
            original_exception=e
        )


def get_channels(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    active_only: bool = False
) -> List[TelegramChannel]:
    """Get list of telegram channels with pagination"""
    logger.debug(f"Fetching telegram channels with skip={skip}, limit={limit}")
    
    try:
        query = db.query(TelegramChannel)
        
        if not include_deleted:
            query = query.filter(TelegramChannel.deleted_at.is_(None))
        
        if active_only:
            query = query.filter(TelegramChannel.is_active == True)
        
        # Order by updated_at desc
        query = query.order_by(TelegramChannel.updated_at.desc())
        
        channels = query.offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(channels)} telegram channels")
        
        return channels
        
    except Exception as e:
        logger.error(f"Error retrieving telegram channels: {e}")
        raise DatabaseException(
            message="Failed to retrieve telegram channels list",
            operation="get_channels",
            table="telegram_channels",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def create_channel(db: Session, channel: TelegramChannelCreate) -> TelegramChannel:
    """Create a new telegram channel"""
    logger.info(f"Creating telegram channel: {channel.name}")
    
    try:
        with atomic_transaction(db):
            # Check if chat_id already exists
            existing_channel = get_channel_by_chat_id(db, channel.chat_id)
            if existing_channel:
                raise ValidationException(
                    message="Telegram channel with this chat_id already exists",
                    details={"chat_id": channel.chat_id, "existing_id": existing_channel.id}
                )
            
            # Validate template exists if provided
            if channel.template_id:
                template = db.query(MessageTemplate).filter(
                    MessageTemplate.id == channel.template_id,
                    MessageTemplate.deleted_at.is_(None)
                ).first()
                if not template:
                    raise ValidationException(
                        message="Template not found",
                        details={"template_id": channel.template_id}
                    )
            
            # Create the channel
            db_channel = TelegramChannel(
                name=channel.name,
                chat_id=channel.chat_id,
                description=channel.description,
                template_id=channel.template_id,
                is_active=channel.is_active,
                auto_post=channel.auto_post,
                send_photos=channel.send_photos,
                disable_web_page_preview=channel.disable_web_page_preview,
                disable_notification=channel.disable_notification
            )
            
            db.add(db_channel)
            db.flush()
            
            logger.info(f"Successfully created telegram channel with ID: {db_channel.id}")
            
    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "UNIQUE constraint failed: telegram_channels.chat_id" in error_msg:
            raise ValidationException(
                message="Telegram channel chat_id already exists",
                details={"chat_id": channel.chat_id},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during telegram channel creation",
                operation="create_channel",
                table="telegram_channels",
                details={"name": channel.name, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to create telegram channel",
            operation="create_channel",
            table="telegram_channels",
            details={"name": channel.name},
            original_exception=e
        )
    
    return db_channel


def update_channel(db: Session, channel_id: int, channel_update: TelegramChannelUpdate) -> TelegramChannel:
    """Update an existing telegram channel"""
    logger.info(f"Updating telegram channel with ID: {channel_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing channel
            channel = get_channel_by_id(db, channel_id)
            if not channel:
                raise ValidationException(
                    message="Telegram channel not found for update",
                    details={"channel_id": channel_id}
                )
            
            # Update fields that are provided
            update_data = channel_update.model_dump(exclude_unset=True, exclude_none=True)
            
            if update_data:
                # Check for chat_id uniqueness if chat_id is being updated
                if 'chat_id' in update_data and update_data['chat_id'] != channel.chat_id:
                    existing_channel = get_channel_by_chat_id(db, update_data['chat_id'])
                    if existing_channel and existing_channel.id != channel_id:
                        raise ValidationException(
                            message="Telegram channel chat_id already exists",
                            details={"chat_id": update_data['chat_id'], "existing_id": existing_channel.id}
                        )
                
                # Validate template exists if being updated
                if 'template_id' in update_data and update_data['template_id']:
                    template = db.query(MessageTemplate).filter(
                        MessageTemplate.id == update_data['template_id'],
                        MessageTemplate.deleted_at.is_(None)
                    ).first()
                    if not template:
                        raise ValidationException(
                            message="Template not found",
                            details={"template_id": update_data['template_id']}
                        )
                
                # Apply updates
                for field, value in update_data.items():
                    setattr(channel, field, value)
                
                # Update the updated_at timestamp
                channel.updated_at = datetime.now(timezone.utc)
                
                db.flush()
                logger.debug(f"Updated telegram channel fields: {list(update_data.keys())}")
            
    except ValidationException:
        raise  # Re-raise validation exceptions
    except IntegrityError as e:
        error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if "UNIQUE constraint failed: telegram_channels.chat_id" in error_msg:
            raise ValidationException(
                message="Telegram channel chat_id already exists",
                details={"channel_id": channel_id},
                original_exception=e
            )
        else:
            raise DatabaseException(
                message="Database constraint violation during telegram channel update",
                operation="update_channel",
                table="telegram_channels",
                details={"channel_id": channel_id, "error": error_msg},
                original_exception=e
            )
    except Exception as e:
        raise DatabaseException(
            message="Failed to update telegram channel",
            operation="update_channel",
            table="telegram_channels",
            details={"channel_id": channel_id},
            original_exception=e
        )
    
    logger.info(f"Successfully updated telegram channel ID: {channel_id}")
    return channel


def soft_delete_channel(db: Session, channel_id: int) -> bool:
    """Soft delete a telegram channel"""
    logger.info(f"Soft deleting telegram channel with ID: {channel_id}")
    
    try:
        with atomic_transaction(db):
            # Get existing channel
            channel = db.query(TelegramChannel).filter(TelegramChannel.id == channel_id).first()
            if not channel:
                raise ValidationException(
                    message="Telegram channel not found for soft deletion",
                    details={"channel_id": channel_id}
                )
            
            # Check if already soft deleted
            if channel.deleted_at is not None:
                logger.warning(f"Telegram channel {channel_id} is already soft deleted at {channel.deleted_at}")
                return True
            
            # Soft delete the channel
            channel.deleted_at = datetime.now(timezone.utc)
            channel.is_active = False
            db.flush()
            
            logger.info(f"Successfully soft deleted telegram channel ID: {channel_id}")
            
        return True
        
    except ValidationException:
        raise  # Re-raise validation exceptions
    except Exception as e:
        logger.error(f"Error soft deleting telegram channel {channel_id}: {e}")
        raise DatabaseException(
            message="Failed to soft delete telegram channel",
            operation="soft_delete_channel",
            table="telegram_channels",
            details={"channel_id": channel_id},
            original_exception=e
        )


def get_channel_count(db: Session, include_deleted: bool = False, active_only: bool = False) -> int:
    """Get total count of telegram channels"""
    try:
        query = db.query(TelegramChannel)
        
        if not include_deleted:
            query = query.filter(TelegramChannel.deleted_at.is_(None))
        
        if active_only:
            query = query.filter(TelegramChannel.is_active == True)
        
        count = query.count()
        logger.debug(f"Total telegram channel count: {count}")
        return count
    except Exception as e:
        logger.error(f"Error getting telegram channel count: {e}")
        raise DatabaseException(
            message="Failed to get telegram channel count",
            operation="get_channel_count",
            table="telegram_channels",
            original_exception=e
        )


# Telegram Post CRUD Operations

def get_post_by_id(db: Session, post_id: int) -> Optional[TelegramPost]:
    """Get telegram post by ID"""
    logger.debug(f"Searching for telegram post with ID: {post_id}")
    
    try:
        post = db.query(TelegramPost).filter(TelegramPost.id == post_id).first()
        
        if post:
            logger.debug(f"Found telegram post for product ID: {post.product_id}")
        else:
            logger.debug(f"No telegram post found for ID: {post_id}")
        
        return post
        
    except Exception as e:
        logger.error(f"Error retrieving telegram post by ID {post_id}: {e}")
        raise DatabaseException(
            message="Failed to retrieve telegram post by ID",
            operation="get_post_by_id",
            table="telegram_posts",
            details={"post_id": post_id},
            original_exception=e
        )


def get_posts(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[PostStatus] = None,
    channel_id: Optional[int] = None,
    product_id: Optional[int] = None
) -> List[TelegramPost]:
    """Get list of telegram posts with filtering"""
    logger.debug(f"Fetching telegram posts with skip={skip}, limit={limit}")
    
    try:
        query = db.query(TelegramPost)
        
        if status:
            query = query.filter(TelegramPost.status == status.value)
        
        if channel_id:
            query = query.filter(TelegramPost.channel_id == channel_id)
        
        if product_id:
            query = query.filter(TelegramPost.product_id == product_id)
        
        # Order by created_at desc
        query = query.order_by(TelegramPost.created_at.desc())
        
        posts = query.offset(skip).limit(limit).all()
        logger.debug(f"Retrieved {len(posts)} telegram posts")
        
        return posts
        
    except Exception as e:
        logger.error(f"Error retrieving telegram posts: {e}")
        raise DatabaseException(
            message="Failed to retrieve telegram posts list",
            operation="get_posts",
            table="telegram_posts",
            details={"skip": skip, "limit": limit},
            original_exception=e
        )


def create_post(db: Session, post: TelegramPostCreate, rendered_content: str) -> TelegramPost:
    """Create a new telegram post"""
    logger.info(f"Creating telegram post for product {post.product_id} to channel {post.channel_id}")
    
    try:
        with atomic_transaction(db):
            # Validate product exists
            product = db.query(Product).filter(
                Product.id == post.product_id,
                Product.deleted_at.is_(None)
            ).first()
            if not product:
                raise ValidationException(
                    message="Product not found",
                    details={"product_id": post.product_id}
                )
            
            # Validate channel exists
            channel = get_channel_by_id(db, post.channel_id)
            if not channel:
                raise ValidationException(
                    message="Telegram channel not found",
                    details={"channel_id": post.channel_id}
                )
            
            # Validate template exists if provided
            if post.template_id:
                template = db.query(MessageTemplate).filter(
                    MessageTemplate.id == post.template_id,
                    MessageTemplate.deleted_at.is_(None)
                ).first()
                if not template:
                    raise ValidationException(
                        message="Template not found",
                        details={"template_id": post.template_id}
                    )
            
            # Create the post
            db_post = TelegramPost(
                product_id=post.product_id,
                channel_id=post.channel_id,
                template_id=post.template_id,
                rendered_content=rendered_content,
                status=PostStatus.PENDING.value
            )
            
            db.add(db_post)
            db.flush()
            
            logger.info(f"Successfully created telegram post with ID: {db_post.id}")
            
    except ValidationException:
        raise  # Re-raise validation exceptions
    except Exception as e:
        raise DatabaseException(
            message="Failed to create telegram post",
            operation="create_post",
            table="telegram_posts",
            details={"product_id": post.product_id, "channel_id": post.channel_id},
            original_exception=e
        )
    
    return db_post


def update_post_status(
    db: Session, 
    post_id: int, 
    status: PostStatus,
    message_id: Optional[int] = None,
    error_message: Optional[str] = None
) -> TelegramPost:
    """Update telegram post status"""
    logger.info(f"Updating telegram post {post_id} status to {status.value}")
    
    try:
        with atomic_transaction(db):
            post = get_post_by_id(db, post_id)
            if not post:
                raise ValidationException(
                    message="Telegram post not found for status update",
                    details={"post_id": post_id}
                )
            
            post.status = status.value
            post.updated_at = datetime.now(timezone.utc)
            
            if status == PostStatus.SENT:
                post.sent_at = datetime.now(timezone.utc)
                if message_id:
                    post.message_id = message_id
                post.error_message = None  # Clear any previous error
            elif status == PostStatus.FAILED:
                post.retry_count += 1
                if error_message:
                    post.error_message = error_message
            
            db.flush()
            
            logger.info(f"Successfully updated telegram post {post_id} status to {status.value}")
            
    except ValidationException:
        raise
    except Exception as e:
        raise DatabaseException(
            message="Failed to update telegram post status",
            operation="update_post_status",
            table="telegram_posts",
            details={"post_id": post_id, "status": status.value},
            original_exception=e
        )
    
    return post


def get_telegram_stats(db: Session) -> Dict[str, Any]:
    """Get telegram statistics"""
    try:
        # Channel stats
        total_channels = db.query(TelegramChannel).filter(TelegramChannel.deleted_at.is_(None)).count()
        active_channels = db.query(TelegramChannel).filter(
            and_(
                TelegramChannel.deleted_at.is_(None),
                TelegramChannel.is_active == True
            )
        ).count()
        
        # Post stats
        total_posts = db.query(TelegramPost).count()
        posts_sent = db.query(TelegramPost).filter(TelegramPost.status == PostStatus.SENT.value).count()
        posts_pending = db.query(TelegramPost).filter(TelegramPost.status == PostStatus.PENDING.value).count()
        posts_failed = db.query(TelegramPost).filter(TelegramPost.status == PostStatus.FAILED.value).count()
        
        # Last post time
        last_post = db.query(TelegramPost).filter(
            TelegramPost.sent_at.isnot(None)
        ).order_by(desc(TelegramPost.sent_at)).first()
        
        return {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "total_posts": total_posts,
            "posts_sent": posts_sent,
            "posts_pending": posts_pending,
            "posts_failed": posts_failed,
            "last_post_at": last_post.sent_at if last_post else None
        }
        
    except Exception as e:
        logger.error(f"Error getting telegram stats: {e}")
        raise DatabaseException(
            message="Failed to get telegram statistics",
            operation="get_telegram_stats",
            table="multiple",
            original_exception=e
        )