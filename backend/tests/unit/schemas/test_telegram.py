"""
Comprehensive unit tests for telegram schemas.

This module contains extensive tests for all Telegram-related Pydantic schemas including
PostStatus enum, TelegramChannelBase, TelegramChannelCreate, TelegramChannelUpdate,
TelegramChannel, TelegramPostBase, TelegramPostCreate, TelegramPost, TelegramPostPreview,
TelegramPostPreviewResponse, SendPostRequest, SendPostResponse, TelegramChannelTest,
TelegramChannelTestResponse, and TelegramStatsResponse.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime
from typing import List

from schemas.telegram import (
    PostStatus,
    TelegramChannelBase, TelegramChannelCreate, TelegramChannelUpdate, TelegramChannel,
    TelegramPostBase, TelegramPostCreate, TelegramPost,
    TelegramPostPreview, TelegramPostPreviewResponse,
    SendPostRequest, SendPostResponse,
    TelegramChannelTest, TelegramChannelTestResponse,
    TelegramStatsResponse
)


class TestPostStatus:
    """Test suite for PostStatus enum."""

    def test_post_status_values(self):
        """Test PostStatus enum values."""
        assert PostStatus.PENDING == "pending"
        assert PostStatus.SENT == "sent"
        assert PostStatus.FAILED == "failed"

    def test_post_status_membership(self):
        """Test PostStatus enum membership."""
        assert "pending" in PostStatus
        assert "sent" in PostStatus
        assert "failed" in PostStatus
        assert "invalid" not in PostStatus

    def test_post_status_iteration(self):
        """Test PostStatus enum iteration."""
        statuses = list(PostStatus)
        assert len(statuses) == 3
        assert PostStatus.PENDING in statuses
        assert PostStatus.SENT in statuses
        assert PostStatus.FAILED in statuses

    def test_post_status_string_representation(self):
        """Test PostStatus string representation."""
        assert PostStatus.PENDING.value == "pending"
        assert PostStatus.SENT.value == "sent"
        assert PostStatus.FAILED.value == "failed"


class TestTelegramChannelBase:
    """Test suite for TelegramChannelBase schema."""

    def test_telegram_channel_base_minimal(self):
        """Test TelegramChannelBase with minimal required fields."""
        channel = TelegramChannelBase(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        assert channel.name == "Test Channel"
        assert channel.chat_id == "-1001234567890"
        assert channel.description is None
        assert channel.template_id is None
        assert channel.is_active is True
        assert channel.auto_post is False
        assert channel.send_photos is True
        assert channel.disable_web_page_preview is True
        assert channel.disable_notification is False

    def test_telegram_channel_base_full(self):
        """Test TelegramChannelBase with all fields."""
        channel = TelegramChannelBase(
            name="Full Test Channel",
            chat_id="@testchannel",
            description="A complete test channel",
            template_id=5,
            is_active=False,
            auto_post=True,
            send_photos=False,
            disable_web_page_preview=False,
            disable_notification=True
        )
        
        assert channel.name == "Full Test Channel"
        assert channel.chat_id == "@testchannel"
        assert channel.description == "A complete test channel"
        assert channel.template_id == 5
        assert channel.is_active is False
        assert channel.auto_post is True
        assert channel.send_photos is False
        assert channel.disable_web_page_preview is False
        assert channel.disable_notification is True

    def test_telegram_channel_base_name_validation(self):
        """Test name field validation."""
        # Valid name
        channel = TelegramChannelBase(name="Valid Name", chat_id="123")
        assert channel.name == "Valid Name"
        
        # Empty name should fail
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="", chat_id="123")
        assert "at least 1 character" in str(exc_info.value)
        
        # Too long name should fail
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name=long_name, chat_id="123")
        assert "at most 100 characters" in str(exc_info.value)

    def test_telegram_channel_base_chat_id_validation(self):
        """Test chat_id field validation."""
        # Valid numeric chat ID (negative)
        channel1 = TelegramChannelBase(name="Test", chat_id="-1001234567890")
        assert channel1.chat_id == "-1001234567890"
        
        # Valid numeric chat ID (positive)
        channel2 = TelegramChannelBase(name="Test", chat_id="1234567890")
        assert channel2.chat_id == "1234567890"
        
        # Valid username format
        channel3 = TelegramChannelBase(name="Test", chat_id="@username")
        assert channel3.chat_id == "@username"
        
        # Valid longer username
        channel4 = TelegramChannelBase(name="Test", chat_id="@my_channel_name")
        assert channel4.chat_id == "@my_channel_name"
        
        # Empty chat_id should fail
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="Test", chat_id="")
        assert "Chat ID cannot be empty" in str(exc_info.value)
        
        # Invalid username (too short)
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="Test", chat_id="@")
        assert "at least 1 character after @" in str(exc_info.value)
        
        # Invalid format (not numeric and not @username)
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="Test", chat_id="invalid_id")
        assert "numeric or start with @" in str(exc_info.value)
        
        # Test numeric validation failure in TelegramChannelUpdate  
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelUpdate(chat_id="not_numeric_or_username")
        assert "numeric or start with @" in str(exc_info.value)
        
        # Test username too short in TelegramChannelUpdate
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelUpdate(chat_id="@")
        assert "at least 1 character after @" in str(exc_info.value)

    def test_telegram_channel_base_description_validation(self):
        """Test description field validation."""
        # Valid description
        channel = TelegramChannelBase(
            name="Test",
            chat_id="123",
            description="Valid description"
        )
        assert channel.description == "Valid description"
        
        # None description is valid
        channel2 = TelegramChannelBase(name="Test", chat_id="123", description=None)
        assert channel2.description is None
        
        # Too long description should fail
        long_desc = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(
                name="Test",
                chat_id="123",
                description=long_desc
            )
        assert "at most 500 characters" in str(exc_info.value)

    def test_telegram_channel_base_template_id_validation(self):
        """Test template_id field validation."""
        # Valid template_id
        channel = TelegramChannelBase(name="Test", chat_id="123", template_id=5)
        assert channel.template_id == 5
        
        # None is valid
        channel2 = TelegramChannelBase(name="Test", chat_id="123", template_id=None)
        assert channel2.template_id is None
        
        # Template ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="Test", chat_id="123", template_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_telegram_channel_base_boolean_fields(self):
        """Test boolean field handling."""
        channel = TelegramChannelBase(
            name="Test",
            chat_id="123",
            is_active=1,  # Truthy value
            auto_post=0,  # Falsy value
            send_photos="true",  # String conversion
            disable_web_page_preview=False,
            disable_notification=True
        )
        
        assert channel.is_active is True
        assert channel.auto_post is False
        assert channel.send_photos is True
        assert channel.disable_web_page_preview is False
        assert channel.disable_notification is True

    def test_telegram_channel_base_required_fields(self):
        """Test required field validation."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(chat_id="123")
        assert "name" in str(exc_info.value)
        
        # Missing chat_id
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelBase(name="Test")
        assert "chat_id" in str(exc_info.value)


class TestTelegramChannelCreate:
    """Test suite for TelegramChannelCreate schema."""

    def test_telegram_channel_create_inheritance(self):
        """Test that TelegramChannelCreate inherits from TelegramChannelBase."""
        channel = TelegramChannelCreate(
            name="Create Test",
            chat_id="@createtest"
        )
        
        assert isinstance(channel, TelegramChannelBase)
        assert channel.name == "Create Test"
        assert channel.chat_id == "@createtest"


class TestTelegramChannelUpdate:
    """Test suite for TelegramChannelUpdate schema."""

    def test_telegram_channel_update_all_optional(self):
        """Test that all TelegramChannelUpdate fields are optional."""
        update = TelegramChannelUpdate()
        
        assert update.name is None
        assert update.chat_id is None
        assert update.description is None
        assert update.template_id is None
        assert update.is_active is None
        assert update.auto_post is None
        assert update.send_photos is None
        assert update.disable_web_page_preview is None
        assert update.disable_notification is None

    def test_telegram_channel_update_partial(self):
        """Test TelegramChannelUpdate with partial data."""
        update = TelegramChannelUpdate(
            name="Updated Name",
            is_active=False,
            auto_post=True
        )
        
        assert update.name == "Updated Name"
        assert update.is_active is False
        assert update.auto_post is True
        assert update.chat_id is None

    def test_telegram_channel_update_chat_id_validation(self):
        """Test chat_id validation in update schema."""
        # Valid chat_id
        update = TelegramChannelUpdate(chat_id="@updated_channel")
        assert update.chat_id == "@updated_channel"
        
        # None is valid (optional)
        update2 = TelegramChannelUpdate(chat_id=None)
        assert update2.chat_id is None
        
        # Empty chat_id should fail (when provided)
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelUpdate(chat_id="")
        assert "Chat ID cannot be empty" in str(exc_info.value)

    def test_telegram_channel_update_validation_consistency(self):
        """Test that update validation is consistent with base schema."""
        # Name validation should be consistent
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelUpdate(name="")
        assert "at least 1 character" in str(exc_info.value)
        
        # Template ID validation should be consistent
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelUpdate(template_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)


class TestTelegramChannel:
    """Test suite for TelegramChannel schema."""

    def test_telegram_channel_full(self):
        """Test complete TelegramChannel schema."""
        now = datetime.now()
        
        channel = TelegramChannel(
            id=1,
            name="Full Test Channel",
            chat_id="@fulltest",
            description="A complete test channel",
            template_id=10,
            is_active=True,
            auto_post=False,
            send_photos=True,
            disable_web_page_preview=False,
            disable_notification=True,
            created_at=now,
            updated_at=now
        )
        
        assert channel.id == 1
        assert channel.name == "Full Test Channel"
        assert channel.chat_id == "@fulltest"
        assert channel.created_at == now
        assert channel.updated_at == now
        assert channel.deleted_at is None

    def test_telegram_channel_with_deleted_at(self):
        """Test TelegramChannel with deleted_at timestamp."""
        now = datetime.now()
        deleted_time = datetime.now()
        
        channel = TelegramChannel(
            id=2,
            name="Deleted Channel",
            chat_id="123",
            created_at=now,
            updated_at=now,
            deleted_at=deleted_time
        )
        
        assert channel.deleted_at == deleted_time

    def test_telegram_channel_inheritance(self):
        """Test that TelegramChannel inherits from TelegramChannelBase."""
        now = datetime.now()
        
        channel = TelegramChannel(
            id=1,
            name="Inheritance Test",
            chat_id="@test",
            created_at=now,
            updated_at=now
        )
        
        assert isinstance(channel, TelegramChannelBase)

    def test_telegram_channel_required_fields(self):
        """Test TelegramChannel required fields."""
        now = datetime.now()
        
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannel(
                name="Test",
                chat_id="123",
                created_at=now,
                updated_at=now
            )
        assert "id" in str(exc_info.value)
        
        # Missing created_at
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannel(
                id=1,
                name="Test",
                chat_id="123",
                updated_at=now
            )
        assert "created_at" in str(exc_info.value)


class TestTelegramPostBase:
    """Test suite for TelegramPostBase schema."""

    def test_telegram_post_base_basic(self):
        """Test basic TelegramPostBase."""
        post = TelegramPostBase(
            product_id=42,
            channel_id=5
        )
        
        assert post.product_id == 42
        assert post.channel_id == 5
        assert post.template_id is None

    def test_telegram_post_base_with_template(self):
        """Test TelegramPostBase with template_id."""
        post = TelegramPostBase(
            product_id=10,
            channel_id=3,
            template_id=7
        )
        
        assert post.product_id == 10
        assert post.channel_id == 3
        assert post.template_id == 7

    def test_telegram_post_base_id_validation(self):
        """Test ID field validation."""
        # Valid IDs
        post = TelegramPostBase(product_id=1, channel_id=1)
        assert post.product_id == 1
        assert post.channel_id == 1
        
        # Product ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostBase(product_id=0, channel_id=1)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Channel ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostBase(product_id=1, channel_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Template ID must be >= 1 (when provided)
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostBase(product_id=1, channel_id=1, template_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_telegram_post_base_required_fields(self):
        """Test required field validation."""
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostBase(channel_id=1)
        assert "product_id" in str(exc_info.value)
        
        # Missing channel_id
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostBase(product_id=1)
        assert "channel_id" in str(exc_info.value)


class TestTelegramPostCreate:
    """Test suite for TelegramPostCreate schema."""

    def test_telegram_post_create_inheritance(self):
        """Test that TelegramPostCreate inherits from TelegramPostBase."""
        post = TelegramPostCreate(
            product_id=15,
            channel_id=8
        )
        
        assert isinstance(post, TelegramPostBase)
        assert post.product_id == 15
        assert post.channel_id == 8


class TestTelegramPost:
    """Test suite for TelegramPost schema."""

    def test_telegram_post_basic(self):
        """Test basic TelegramPost."""
        now = datetime.now()
        
        post = TelegramPost(
            id=1,
            product_id=42,
            channel_id=5,
            rendered_content="Test post content",
            status=PostStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        assert post.id == 1
        assert post.product_id == 42
        assert post.channel_id == 5
        assert post.rendered_content == "Test post content"
        assert post.status == PostStatus.PENDING
        assert post.message_id is None
        assert post.sent_at is None
        assert post.error_message is None
        assert post.retry_count == 0

    def test_telegram_post_sent(self):
        """Test TelegramPost in sent state."""
        now = datetime.now()
        sent_time = datetime.now()
        
        post = TelegramPost(
            id=2,
            product_id=10,
            channel_id=3,
            message_id=12345,
            rendered_content="Sent post content",
            sent_at=sent_time,
            status=PostStatus.SENT,
            retry_count=1,
            created_at=now,
            updated_at=now
        )
        
        assert post.message_id == 12345
        assert post.sent_at == sent_time
        assert post.status == PostStatus.SENT
        assert post.retry_count == 1

    def test_telegram_post_failed(self):
        """Test TelegramPost in failed state."""
        now = datetime.now()
        
        post = TelegramPost(
            id=3,
            product_id=20,
            channel_id=7,
            rendered_content="Failed post content",
            status=PostStatus.FAILED,
            error_message="Network timeout",
            retry_count=3,
            created_at=now,
            updated_at=now
        )
        
        assert post.status == PostStatus.FAILED
        assert post.error_message == "Network timeout"
        assert post.retry_count == 3

    def test_telegram_post_required_fields(self):
        """Test TelegramPost required fields."""
        now = datetime.now()
        
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            TelegramPost(
                product_id=1,
                channel_id=1,
                rendered_content="Content",
                status=PostStatus.PENDING,
                created_at=now,
                updated_at=now
            )
        assert "id" in str(exc_info.value)
        
        # Missing rendered_content
        with pytest.raises(ValidationError) as exc_info:
            TelegramPost(
                id=1,
                product_id=1,
                channel_id=1,
                status=PostStatus.PENDING,
                created_at=now,
                updated_at=now
            )
        assert "rendered_content" in str(exc_info.value)
        
        # Missing status
        with pytest.raises(ValidationError) as exc_info:
            TelegramPost(
                id=1,
                product_id=1,
                channel_id=1,
                rendered_content="Content",
                created_at=now,
                updated_at=now
            )
        assert "status" in str(exc_info.value)

    def test_telegram_post_inheritance(self):
        """Test that TelegramPost inherits from TelegramPostBase."""
        now = datetime.now()
        
        post = TelegramPost(
            id=1,
            product_id=1,
            channel_id=1,
            rendered_content="Test",
            status=PostStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        assert isinstance(post, TelegramPostBase)


class TestTelegramPostPreview:
    """Test suite for TelegramPostPreview schema."""

    def test_telegram_post_preview_minimal(self):
        """Test TelegramPostPreview with minimal data."""
        preview = TelegramPostPreview(product_id=42)
        
        assert preview.product_id == 42
        assert preview.channel_id is None
        assert preview.template_id is None
        assert preview.template_content is None

    def test_telegram_post_preview_full(self):
        """Test TelegramPostPreview with all fields."""
        preview = TelegramPostPreview(
            product_id=42,
            channel_id=5,
            template_id=10,
            template_content="Custom template: {product_name}"
        )
        
        assert preview.product_id == 42
        assert preview.channel_id == 5
        assert preview.template_id == 10
        assert preview.template_content == "Custom template: {product_name}"

    def test_telegram_post_preview_validation(self):
        """Test TelegramPostPreview validation."""
        # Product ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreview(product_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Channel ID must be >= 1 (when provided)
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreview(product_id=1, channel_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Template ID must be >= 1 (when provided)
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreview(product_id=1, template_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)


class TestTelegramPostPreviewResponse:
    """Test suite for TelegramPostPreviewResponse schema."""

    def test_telegram_post_preview_response_basic(self):
        """Test basic TelegramPostPreviewResponse."""
        response = TelegramPostPreviewResponse(
            rendered_content="Product: Test Item - $29.99",
            template_used="Default Template",
            product_name="Test Item"
        )
        
        assert response.rendered_content == "Product: Test Item - $29.99"
        assert response.template_used == "Default Template"
        assert response.product_name == "Test Item"
        assert response.channel_name is None
        assert response.will_send_photos is True
        assert response.photo_count == 0

    def test_telegram_post_preview_response_full(self):
        """Test TelegramPostPreviewResponse with all fields."""
        response = TelegramPostPreviewResponse(
            rendered_content="Full preview content",
            template_used="Custom Template",
            product_name="Full Product",
            channel_name="Test Channel",
            will_send_photos=False,
            photo_count=3
        )
        
        assert response.rendered_content == "Full preview content"
        assert response.template_used == "Custom Template"
        assert response.product_name == "Full Product"
        assert response.channel_name == "Test Channel"
        assert response.will_send_photos is False
        assert response.photo_count == 3

    def test_telegram_post_preview_response_required_fields(self):
        """Test required fields validation."""
        # Missing rendered_content
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreviewResponse(
                template_used="Template",
                product_name="Product"
            )
        assert "rendered_content" in str(exc_info.value)
        
        # Missing template_used
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreviewResponse(
                rendered_content="Content",
                product_name="Product"
            )
        assert "template_used" in str(exc_info.value)
        
        # Missing product_name
        with pytest.raises(ValidationError) as exc_info:
            TelegramPostPreviewResponse(
                rendered_content="Content",
                template_used="Template"
            )
        assert "product_name" in str(exc_info.value)


class TestSendPostRequest:
    """Test suite for SendPostRequest schema."""

    def test_send_post_request_basic(self):
        """Test basic SendPostRequest."""
        request = SendPostRequest(
            product_id=42,
            channel_ids=[1, 2, 3]
        )
        
        assert request.product_id == 42
        assert request.channel_ids == [1, 2, 3]
        assert request.template_id is None
        assert request.template_content is None
        assert request.send_photos is None
        assert request.disable_notification is None

    def test_send_post_request_full(self):
        """Test SendPostRequest with all fields."""
        request = SendPostRequest(
            product_id=42,
            channel_ids=[5, 10],
            template_id=7,
            template_content="Custom content: {product_name}",
            send_photos=False,
            disable_notification=True
        )
        
        assert request.product_id == 42
        assert request.channel_ids == [5, 10]
        assert request.template_id == 7
        assert request.template_content == "Custom content: {product_name}"
        assert request.send_photos is False
        assert request.disable_notification is True

    def test_send_post_request_validation(self):
        """Test SendPostRequest validation."""
        # Product ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            SendPostRequest(product_id=0, channel_ids=[1])
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Channel IDs list must not be empty
        with pytest.raises(ValidationError) as exc_info:
            SendPostRequest(product_id=1, channel_ids=[])
        assert "at least 1 item" in str(exc_info.value)
        
        # Template ID must be >= 1 (when provided)
        with pytest.raises(ValidationError) as exc_info:
            SendPostRequest(product_id=1, channel_ids=[1], template_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_send_post_request_channel_ids_types(self):
        """Test channel_ids type handling."""
        # List of integers
        request1 = SendPostRequest(product_id=1, channel_ids=[1, 2, 3])
        assert request1.channel_ids == [1, 2, 3]
        
        # List of string numbers (should convert)
        request2 = SendPostRequest(product_id=1, channel_ids=["1", "2", "3"])
        assert request2.channel_ids == [1, 2, 3]

    def test_send_post_request_required_fields(self):
        """Test required field validation."""
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            SendPostRequest(channel_ids=[1])
        assert "product_id" in str(exc_info.value)
        
        # Missing channel_ids
        with pytest.raises(ValidationError) as exc_info:
            SendPostRequest(product_id=1)
        assert "channel_ids" in str(exc_info.value)


class TestSendPostResponse:
    """Test suite for SendPostResponse schema."""

    def test_send_post_response_basic(self):
        """Test basic SendPostResponse."""
        now = datetime.now()
        
        posts = [
            TelegramPost(
                id=1,
                product_id=42,
                channel_id=5,
                rendered_content="Post 1",
                status=PostStatus.SENT,
                created_at=now,
                updated_at=now
            ),
            TelegramPost(
                id=2,
                product_id=42,
                channel_id=6,
                rendered_content="Post 2",
                status=PostStatus.FAILED,
                created_at=now,
                updated_at=now
            )
        ]
        
        response = SendPostResponse(
            posts_created=posts,
            success_count=1,
            failed_count=1,
            errors=["Channel 6 connection failed"]
        )
        
        assert len(response.posts_created) == 2
        assert response.success_count == 1
        assert response.failed_count == 1
        assert response.errors == ["Channel 6 connection failed"]

    def test_send_post_response_all_success(self):
        """Test SendPostResponse with all successful posts."""
        now = datetime.now()
        
        posts = [
            TelegramPost(
                id=1,
                product_id=10,
                channel_id=1,
                rendered_content="Success 1",
                status=PostStatus.SENT,
                created_at=now,
                updated_at=now
            )
        ]
        
        response = SendPostResponse(
            posts_created=posts,
            success_count=1,
            failed_count=0
        )
        
        assert response.success_count == 1
        assert response.failed_count == 0
        assert response.errors == []

    def test_send_post_response_required_fields(self):
        """Test required field validation."""
        # Missing posts_created
        with pytest.raises(ValidationError) as exc_info:
            SendPostResponse(
                success_count=1,
                failed_count=0
            )
        assert "posts_created" in str(exc_info.value)
        
        # Missing success_count
        with pytest.raises(ValidationError) as exc_info:
            SendPostResponse(
                posts_created=[],
                failed_count=0
            )
        assert "success_count" in str(exc_info.value)
        
        # Missing failed_count
        with pytest.raises(ValidationError) as exc_info:
            SendPostResponse(
                posts_created=[],
                success_count=1
            )
        assert "failed_count" in str(exc_info.value)


class TestTelegramChannelTest:
    """Test suite for TelegramChannelTest schema."""

    def test_telegram_channel_test_basic(self):
        """Test basic TelegramChannelTest."""
        test = TelegramChannelTest(chat_id="@testchannel")
        assert test.chat_id == "@testchannel"

    def test_telegram_channel_test_numeric_id(self):
        """Test TelegramChannelTest with numeric chat_id."""
        test = TelegramChannelTest(chat_id="-1001234567890")
        assert test.chat_id == "-1001234567890"

    def test_telegram_channel_test_required_field(self):
        """Test required field validation."""
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelTest()
        assert "chat_id" in str(exc_info.value)


class TestTelegramChannelTestResponse:
    """Test suite for TelegramChannelTestResponse schema."""

    def test_telegram_channel_test_response_success(self):
        """Test successful TelegramChannelTestResponse."""
        chat_info = {
            "id": -1001234567890,
            "title": "Test Channel",
            "type": "channel"
        }
        
        response = TelegramChannelTestResponse(
            success=True,
            chat_info=chat_info
        )
        
        assert response.success is True
        assert response.chat_info == chat_info
        assert response.error is None

    def test_telegram_channel_test_response_failure(self):
        """Test failed TelegramChannelTestResponse."""
        response = TelegramChannelTestResponse(
            success=False,
            error="Channel not found"
        )
        
        assert response.success is False
        assert response.error == "Channel not found"
        assert response.chat_info is None

    def test_telegram_channel_test_response_required_field(self):
        """Test required field validation."""
        with pytest.raises(ValidationError) as exc_info:
            TelegramChannelTestResponse()
        assert "success" in str(exc_info.value)


class TestTelegramStatsResponse:
    """Test suite for TelegramStatsResponse schema."""

    def test_telegram_stats_response_basic(self):
        """Test basic TelegramStatsResponse."""
        response = TelegramStatsResponse(
            total_channels=10,
            active_channels=8,
            total_posts=100,
            posts_sent=85,
            posts_pending=10,
            posts_failed=5
        )
        
        assert response.total_channels == 10
        assert response.active_channels == 8
        assert response.total_posts == 100
        assert response.posts_sent == 85
        assert response.posts_pending == 10
        assert response.posts_failed == 5
        assert response.last_post_at is None

    def test_telegram_stats_response_with_last_post(self):
        """Test TelegramStatsResponse with last_post_at."""
        last_post_time = datetime.now()
        
        response = TelegramStatsResponse(
            total_channels=5,
            active_channels=5,
            total_posts=50,
            posts_sent=45,
            posts_pending=3,
            posts_failed=2,
            last_post_at=last_post_time
        )
        
        assert response.last_post_at == last_post_time

    def test_telegram_stats_response_zero_values(self):
        """Test TelegramStatsResponse with zero values."""
        response = TelegramStatsResponse(
            total_channels=0,
            active_channels=0,
            total_posts=0,
            posts_sent=0,
            posts_pending=0,
            posts_failed=0
        )
        
        assert response.total_channels == 0
        assert response.active_channels == 0
        assert response.total_posts == 0

    def test_telegram_stats_response_required_fields(self):
        """Test required field validation."""
        # Missing total_channels
        with pytest.raises(ValidationError) as exc_info:
            TelegramStatsResponse(
                active_channels=1,
                total_posts=1,
                posts_sent=1,
                posts_pending=0,
                posts_failed=0
            )
        assert "total_channels" in str(exc_info.value)
        
        # Test all required fields are validated
        required_fields = [
            "total_channels", "active_channels", "total_posts",
            "posts_sent", "posts_pending", "posts_failed"
        ]
        
        for field in required_fields:
            kwargs = {f: 0 for f in required_fields}
            del kwargs[field]
            
            with pytest.raises(ValidationError) as exc_info:
                TelegramStatsResponse(**kwargs)
            assert field in str(exc_info.value)


class TestTelegramSchemaIntegration:
    """Test integration between telegram schemas."""

    def test_telegram_workflow_integration(self):
        """Test complete Telegram workflow through schemas."""
        now = datetime.now()
        
        # 1. Create channel
        channel_create = TelegramChannelCreate(
            name="Integration Test Channel",
            chat_id="@integrationtest",
            description="Testing workflow integration"
        )
        
        # 2. Convert to full channel
        channel = TelegramChannel(
            id=1,
            name=channel_create.name,
            chat_id=channel_create.chat_id,
            description=channel_create.description,
            created_at=now,
            updated_at=now
        )
        
        # 3. Create post
        post_create = TelegramPostCreate(
            product_id=42,
            channel_id=channel.id
        )
        
        # 4. Preview post
        preview = TelegramPostPreview(
            product_id=post_create.product_id,
            channel_id=post_create.channel_id
        )
        
        # 5. Send post
        send_request = SendPostRequest(
            product_id=post_create.product_id,
            channel_ids=[channel.id]
        )
        
        # Verify workflow consistency
        assert channel.name == "Integration Test Channel"
        assert post_create.channel_id == channel.id
        assert preview.product_id == post_create.product_id
        assert send_request.channel_ids == [channel.id]

    def test_telegram_error_handling_integration(self):
        """Test error handling across Telegram schemas."""
        # Consistent ID validation across schemas
        invalid_id = 0
        
        # Channel template_id validation
        with pytest.raises(ValidationError):
            TelegramChannelBase(
                name="Test",
                chat_id="123",
                template_id=invalid_id
            )
        
        # Post product_id validation
        with pytest.raises(ValidationError):
            TelegramPostBase(
                product_id=invalid_id,
                channel_id=1
            )
        
        # Preview product_id validation
        with pytest.raises(ValidationError):
            TelegramPostPreview(product_id=invalid_id)
        
        # Send request product_id validation
        with pytest.raises(ValidationError):
            SendPostRequest(
                product_id=invalid_id,
                channel_ids=[1]
            )

    def test_telegram_data_consistency(self):
        """Test data consistency between related schemas."""
        now = datetime.now()
        
        # Create related objects with consistent data
        channel = TelegramChannel(
            id=5,
            name="Consistency Test",
            chat_id="@consistency",
            template_id=10,
            created_at=now,
            updated_at=now
        )
        
        post = TelegramPost(
            id=1,
            product_id=42,
            channel_id=channel.id,  # Should match channel
            template_id=channel.template_id,  # Should match channel's template
            rendered_content="Test content",
            status=PostStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        # Verify consistency
        assert post.channel_id == channel.id
        assert post.template_id == channel.template_id

    def test_telegram_serialization_integration(self):
        """Test serialization consistency across schemas."""
        now = datetime.now()
        
        # Create complex nested structure
        posts = [
            TelegramPost(
                id=1,
                product_id=10,
                channel_id=1,
                rendered_content="Post 1",
                status=PostStatus.SENT,
                created_at=now,
                updated_at=now
            ),
            TelegramPost(
                id=2,
                product_id=10,
                channel_id=2,
                rendered_content="Post 2",
                status=PostStatus.FAILED,
                error_message="Failed to send",
                created_at=now,
                updated_at=now
            )
        ]
        
        send_response = SendPostResponse(
            posts_created=posts,
            success_count=1,
            failed_count=1,
            errors=["Channel 2 error"]
        )
        
        # Test serialization
        json_data = send_response.model_dump()
        
        assert len(json_data["posts_created"]) == 2
        assert json_data["success_count"] == 1
        assert json_data["failed_count"] == 1
        assert json_data["errors"] == ["Channel 2 error"]
        
        # Verify nested post serialization
        assert json_data["posts_created"][0]["status"] == "sent"
        assert json_data["posts_created"][1]["status"] == "failed"
        assert json_data["posts_created"][1]["error_message"] == "Failed to send"