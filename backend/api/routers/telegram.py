"""
API router for Telegram functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from database.session import get_db
from schemas.telegram import (
    TelegramChannel, TelegramChannelCreate, TelegramChannelUpdate,
    TelegramPost, TelegramPostPreview, TelegramPostPreviewResponse,
    SendPostRequest, SendPostResponse, TelegramChannelTest, TelegramChannelTestResponse,
    TelegramStatsResponse, PostStatus
)
from schemas.base import PaginatedResponse, APIResponse, PaginationInfo
from crud.telegram import (
    get_channels, get_channel_by_id, create_channel, update_channel, soft_delete_channel,
    get_channel_count, get_posts, get_post_by_id, get_telegram_stats
)
from services.telegram_post_service import telegram_post_service
from services.telegram_service import telegram_service
from utils.logger import get_logger
from exceptions.base import ValidationException, ExternalServiceException

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


# Channel Management Endpoints

@router.get("/channels", response_model=PaginatedResponse[TelegramChannel])
async def get_channels_list(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
        active_only: bool = Query(False, description="Return only active channels"),
        include_deleted: bool = Query(False, description="Include soft-deleted channels"),
        db: Session = Depends(get_db)
) -> PaginatedResponse[TelegramChannel]:
    """Get list of telegram channels with pagination"""
    try:
        channels = get_channels(
            db=db,
            skip=skip,
            limit=limit,
            active_only=active_only,
            include_deleted=include_deleted
        )
        total = get_channel_count(db=db, active_only=active_only, include_deleted=include_deleted)

        # Convert SQLAlchemy models to Pydantic schemas
        channel_schemas = [TelegramChannel.model_validate(channel) for channel in channels]

        return PaginatedResponse(
            success=True,
            data=channel_schemas,
            pagination=PaginationInfo(
                total=total,
                skip=skip,
                limit=limit,
                has_more=(skip + limit) < total
            )
        )
    except Exception as e:
        logger.error(f"Error getting channels list: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channels")


@router.get("/channels/{channel_id}", response_model=APIResponse[TelegramChannel])
async def get_channel(
        channel_id: int,
        include_deleted: bool = Query(False, description="Include soft-deleted channel"),
        db: Session = Depends(get_db)
) -> APIResponse[TelegramChannel]:
    """Get telegram channel by ID"""
    try:
        channel = get_channel_by_id(db=db, channel_id=channel_id, include_deleted=include_deleted)
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        return APIResponse(success=True, data=TelegramChannel.model_validate(channel))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channel")


@router.post("/channels", response_model=APIResponse[TelegramChannel])
async def create_telegram_channel(
        channel: TelegramChannelCreate,
        db: Session = Depends(get_db)
) -> APIResponse[TelegramChannel]:
    """Create a new telegram channel"""
    try:
        created_channel = create_channel(db=db, channel=channel)
        db.commit()

        return APIResponse(
            success=True,
            message="Telegram channel created successfully",
            data=TelegramChannel.model_validate(created_channel)
        )
    except ValidationException as e:
        logger.warning(f"Validation error creating channel: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating channel: {e}")
        raise HTTPException(status_code=500, detail="Failed to create channel")


@router.put("/channels/{channel_id}", response_model=APIResponse[TelegramChannel])
async def update_telegram_channel(
        channel_id: int,
        channel_update: TelegramChannelUpdate,
        db: Session = Depends(get_db)
) -> APIResponse[TelegramChannel]:
    """Update telegram channel"""
    try:
        updated_channel = update_channel(db=db, channel_id=channel_id, channel_update=channel_update)
        db.commit()

        return APIResponse(
            success=True,
            message="Telegram channel updated successfully",
            data=TelegramChannel.model_validate(updated_channel)
        )
    except ValidationException as e:
        logger.warning(f"Validation error updating channel {channel_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update channel")


@router.delete("/channels/{channel_id}", response_model=APIResponse[Dict[str, Any]])
async def delete_telegram_channel(
        channel_id: int,
        db: Session = Depends(get_db)
) -> APIResponse[Dict[str, Any]]:
    """Soft delete telegram channel"""
    try:
        success = soft_delete_channel(db=db, channel_id=channel_id)
        db.commit()

        if success:
            return APIResponse(
                success=True,
                message="Telegram channel deleted successfully",
                data={"channel_id": channel_id, "deleted": True}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to delete channel")
    except ValidationException as e:
        logger.warning(f"Validation error deleting channel {channel_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete channel")


@router.post("/channels/test", response_model=TelegramChannelTestResponse)
async def test_telegram_channel(
        test_request: TelegramChannelTest
) -> TelegramChannelTestResponse:
    """Test telegram channel connection"""
    try:
        if not telegram_service.is_enabled():
            return TelegramChannelTestResponse(
                success=False,
                error="Telegram service is disabled - bot token not configured"
            )

        chat_info = await telegram_service.get_chat_info(test_request.chat_id)

        return TelegramChannelTestResponse(
            success=True,
            chat_info=chat_info.get("result", {})
        )
    except ExternalServiceException as e:
        logger.warning(f"Telegram API error testing channel: {e}")
        return TelegramChannelTestResponse(
            success=False,
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error testing telegram channel: {e}")
        return TelegramChannelTestResponse(
            success=False,
            error="Failed to test channel connection"
        )


# Post Management Endpoints

@router.get("/posts", response_model=PaginatedResponse[TelegramPost])
async def get_posts_list(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
        status: Optional[PostStatus] = Query(None, description="Filter by post status"),
        channel_id: Optional[int] = Query(None, ge=1, description="Filter by channel ID"),
        product_id: Optional[int] = Query(None, ge=1, description="Filter by product ID"),
        db: Session = Depends(get_db)
) -> PaginatedResponse[TelegramPost]:
    """Get list of telegram posts with filtering"""
    try:
        posts = get_posts(
            db=db,
            skip=skip,
            limit=limit,
            status=status,
            channel_id=channel_id,
            product_id=product_id
        )

        # Count total with same filters
        from models.product import TelegramPost as TelegramPostModel

        query = db.query(TelegramPostModel)
        if status:
            query = query.filter(TelegramPostModel.status == status.value)
        if channel_id:
            query = query.filter(TelegramPostModel.channel_id == channel_id)
        if product_id:
            query = query.filter(TelegramPostModel.product_id == product_id)

        total = query.count()

        # Convert SQLAlchemy models to Pydantic schemas
        post_schemas = [TelegramPost.model_validate(post) for post in posts]

        return PaginatedResponse(
            success=True,
            data=post_schemas,
            pagination=PaginationInfo(
                total=total,
                skip=skip,
                limit=limit,
                has_more=(skip + limit) < total
            )
        )
    except Exception as e:
        logger.error(f"Error getting posts list: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve posts")


@router.get("/posts/{post_id}", response_model=APIResponse[TelegramPost])
async def get_post(
        post_id: int,
        db: Session = Depends(get_db)
) -> APIResponse[TelegramPost]:
    """Get telegram post by ID"""
    try:
        post = get_post_by_id(db=db, post_id=post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        return APIResponse(success=True, data=TelegramPost.model_validate(post))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post {post_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve post")


@router.post("/posts/preview", response_model=TelegramPostPreviewResponse)
async def preview_telegram_post(
        preview_request: TelegramPostPreview,
        db: Session = Depends(get_db)
) -> TelegramPostPreviewResponse:
    """Preview how a telegram post will look"""
    try:
        preview_data = await telegram_post_service.preview_post(
            db=db,
            product_id=preview_request.product_id,
            channel_id=preview_request.channel_id,
            template_id=preview_request.template_id,
            template_content=preview_request.template_content
        )

        return TelegramPostPreviewResponse(**preview_data)
    except ValidationException as e:
        logger.warning(f"Validation error previewing post: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error previewing telegram post: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview post")


@router.post("/posts/send", response_model=SendPostResponse)
async def send_telegram_post(
        send_request: SendPostRequest,
        db: Session = Depends(get_db)
) -> SendPostResponse:
    """Send a product post to telegram channels"""
    try:
        result = await telegram_post_service.send_post(
            db=db,
            product_id=send_request.product_id,
            channel_ids=send_request.channel_ids,
            template_id=send_request.template_id,
            template_content=send_request.template_content,
            send_photos=send_request.send_photos,
            disable_notification=send_request.disable_notification
        )

        return SendPostResponse(**result)
    except ValidationException as e:
        logger.warning(f"Validation error sending post: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Error sending telegram post: {e}")
        raise HTTPException(status_code=500, detail="Failed to send post")


@router.post("/posts/retry", response_model=APIResponse[Dict[str, Any]])
async def retry_failed_posts(
        max_retries: int = Query(3, ge=1, le=10, description="Maximum retry attempts"),
        db: Session = Depends(get_db)
) -> APIResponse[Dict[str, Any]]:
    """Retry failed telegram posts"""
    try:
        result = await telegram_post_service.retry_failed_posts(db=db, max_retries=max_retries)

        return APIResponse(
            success=True,
            message="Failed posts retry completed",
            data=result
        )
    except Exception as e:
        logger.error(f"Error retrying failed posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry posts")


# Statistics and Info Endpoints

@router.get("/stats", response_model=TelegramStatsResponse)
async def get_telegram_statistics(
        db: Session = Depends(get_db)
) -> TelegramStatsResponse:
    """Get telegram usage statistics"""
    try:
        stats = get_telegram_stats(db=db)
        return TelegramStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting telegram stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/status", response_model=APIResponse[Dict[str, Any]])
async def get_telegram_service_status() -> APIResponse[Dict[str, Any]]:
    """Get telegram service status"""
    try:
        is_enabled = telegram_service.is_enabled()

        status_info = {
            "service_enabled": is_enabled,
            "bot_token_configured": bool(telegram_service.bot_token) if is_enabled else False
        }

        if is_enabled:
            try:
                # Test basic API connectivity
                await telegram_service.get_me() if hasattr(telegram_service, 'get_me') else None
                status_info["api_accessible"] = True
            except Exception:
                status_info["api_accessible"] = False
        else:
            status_info["api_accessible"] = False

        return APIResponse(
            success=True,
            message="Telegram service status retrieved",
            data=status_info
        )
    except Exception as e:
        logger.error(f"Error getting telegram service status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get service status")
