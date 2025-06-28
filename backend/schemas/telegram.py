"""
Pydantic schemas for Telegram functionality
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class PostStatus(str, Enum):
    """Telegram post status enum"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class TelegramChannelBase(BaseModel):
    """Base schema for Telegram channel"""
    name: str = Field(..., min_length=1, max_length=100, description="Channel display name")
    chat_id: str = Field(..., description="Telegram chat ID or @username")
    description: Optional[str] = Field(None, max_length=500, description="Channel description")
    template_id: Optional[int] = Field(None, ge=1, description="Default template ID")
    is_active: bool = Field(True, description="Whether channel is active")
    auto_post: bool = Field(False, description="Whether to auto-post new products")
    send_photos: bool = Field(True, description="Whether to include product photos")
    disable_web_page_preview: bool = Field(True, description="Disable link previews")
    disable_notification: bool = Field(False, description="Send messages silently")
    
    @field_validator('chat_id')
    @classmethod
    def validate_chat_id(cls, v):
        """Validate chat ID format"""
        if not v:
            raise ValueError("Chat ID cannot be empty")
        
        # Accept numeric IDs (positive/negative) or @username format
        if v.startswith('@'):
            if len(v) < 2:
                raise ValueError("Username must have at least 1 character after @")
        else:
            try:
                int(v)  # Should be numeric
            except ValueError:
                raise ValueError("Chat ID must be numeric or start with @")
        
        return v


class TelegramChannelCreate(TelegramChannelBase):
    """Schema for creating a Telegram channel"""
    pass


class TelegramChannelUpdate(BaseModel):
    """Schema for updating a Telegram channel"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    chat_id: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    template_id: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    auto_post: Optional[bool] = None
    send_photos: Optional[bool] = None
    disable_web_page_preview: Optional[bool] = None
    disable_notification: Optional[bool] = None
    
    @field_validator('chat_id')
    @classmethod
    def validate_chat_id(cls, v):
        """Validate chat ID format"""
        if v is None:
            return v
        
        if not v:
            raise ValueError("Chat ID cannot be empty")
        
        # Accept numeric IDs (positive/negative) or @username format
        if v.startswith('@'):
            if len(v) < 2:
                raise ValueError("Username must have at least 1 character after @")
        else:
            try:
                int(v)  # Should be numeric
            except ValueError:
                raise ValueError("Chat ID must be numeric or start with @")
        
        return v


class TelegramChannel(TelegramChannelBase):
    """Schema for Telegram channel response"""
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class TelegramPostBase(BaseModel):
    """Base schema for Telegram post"""
    product_id: int = Field(..., ge=1, description="Product ID to post")
    channel_id: int = Field(..., ge=1, description="Channel ID to post to")
    template_id: Optional[int] = Field(None, ge=1, description="Template ID to use")


class TelegramPostCreate(TelegramPostBase):
    """Schema for creating a Telegram post"""
    pass


class TelegramPost(TelegramPostBase):
    """Schema for Telegram post response"""
    id: int
    message_id: Optional[int] = None
    rendered_content: str
    sent_at: Optional[datetime] = None
    status: PostStatus
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TelegramPostPreview(BaseModel):
    """Schema for telegram post preview"""
    product_id: int = Field(..., ge=1, description="Product ID to preview")
    channel_id: Optional[int] = Field(None, ge=1, description="Channel ID (for template)")
    template_id: Optional[int] = Field(None, ge=1, description="Template ID to use")
    template_content: Optional[str] = Field(None, description="Custom template content")


class TelegramPostPreviewResponse(BaseModel):
    """Schema for telegram post preview response"""
    rendered_content: str
    template_used: str
    product_name: str
    channel_name: Optional[str] = None
    will_send_photos: bool = True
    photo_count: int = 0


class SendPostRequest(BaseModel):
    """Schema for sending a telegram post"""
    product_id: int = Field(..., ge=1, description="Product ID to post")
    channel_ids: List[int] = Field(..., min_length=1, description="Channel IDs to post to")
    template_id: Optional[int] = Field(None, ge=1, description="Template ID to use")
    template_content: Optional[str] = Field(None, description="Custom template content")
    send_photos: Optional[bool] = Field(None, description="Override channel photo setting")
    disable_notification: Optional[bool] = Field(None, description="Override notification setting")


class SendPostResponse(BaseModel):
    """Schema for send post response"""
    posts_created: List[TelegramPost]
    success_count: int
    failed_count: int
    errors: List[str] = []


class TelegramChannelTest(BaseModel):
    """Schema for testing telegram channel connection"""
    chat_id: str = Field(..., description="Telegram chat ID to test")


class TelegramChannelTestResponse(BaseModel):
    """Schema for telegram channel test response"""
    success: bool
    chat_info: Optional[dict] = None
    error: Optional[str] = None


class TelegramStatsResponse(BaseModel):
    """Schema for telegram statistics response"""
    total_channels: int
    active_channels: int
    total_posts: int
    posts_sent: int
    posts_pending: int
    posts_failed: int
    last_post_at: Optional[datetime] = None