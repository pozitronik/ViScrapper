"""
Tests for Telegram functionality
"""
import pytest
from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database.session import get_db, engine
from models.product import Base, Product, Image, Size, MessageTemplate, TelegramChannel, TelegramPost
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from crud.telegram import create_channel, get_channel_by_id, create_post
from crud.template import create_template
from schemas.telegram import TelegramChannelCreate, TelegramPostCreate, PostStatus
from schemas.template import MessageTemplateCreate
from services.telegram_service import TelegramService
from services.telegram_post_service import TelegramPostService


class TestTelegramService:
    """Test telegram service functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database"""
        # Create isolated test database
        test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=test_engine)
        yield
        Base.metadata.drop_all(bind=test_engine)
    
    def test_telegram_service_disabled_without_token(self):
        """Test that service is disabled without token"""
        service = TelegramService(bot_token=None)
        assert not service.is_enabled()
    
    def test_telegram_service_enabled_with_token(self):
        """Test that service is enabled with token"""
        service = TelegramService(bot_token="fake_token")
        assert service.is_enabled()
    
    @pytest.mark.asyncio
    async def test_send_message_disabled_service(self):
        """Test send message with disabled service"""
        service = TelegramService(bot_token=None)
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            await service.send_message("123", "test message")
        
        assert "disabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_message_invalid_params(self):
        """Test send message with invalid parameters"""
        service = TelegramService(bot_token="fake_token")
        
        from exceptions.base import ValidationException
        
        # Empty chat_id
        with pytest.raises(ValidationException):
            await service.send_message("", "test message")
        
        # Empty text
        with pytest.raises(ValidationException):
            await service.send_message("123", "")
        
        # Text too long
        with pytest.raises(ValidationException):
            await service.send_message("123", "x" * 5000)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": True,
            "result": {"message_id": 123, "text": "test message"}
        }
        mock_post.return_value = mock_response
        
        service = TelegramService(bot_token="fake_token")
        result = await service.send_message("123", "test message")
        
        assert result["ok"] is True
        assert result["result"]["message_id"] == 123
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.post')
    async def test_send_message_api_error(self, mock_post):
        """Test message sending with API error"""
        # Mock API error response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ok": False,
            "description": "Chat not found"
        }
        mock_post.return_value = mock_response
        
        service = TelegramService(bot_token="fake_token")
        
        from exceptions.base import ExternalServiceException
        with pytest.raises(ExternalServiceException) as exc_info:
            await service.send_message("123", "test message")
        
        assert "Chat not found" in str(exc_info.value)


class TestTelegramCRUD:
    """Test telegram CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        yield
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def create_test_template(self, db: Session) -> MessageTemplate:
        """Helper to create test template"""
        template_data = MessageTemplateCreate(
            name="Test Template",
            description="A test template",
            template_content="Product: {product_name} - Price: {product_price}",
            is_active=True
        )
        return create_template(db, template_data)
    
    def test_create_channel_success(self):
        """Test successful channel creation"""
        db = self.test_db
        
        # Create template first
        template = self.create_test_template(db)
        
        channel_data = TelegramChannelCreate(
            name="Test Channel",
            chat_id="@testchannel",
            description="A test channel",
            template_id=template.id,
            is_active=True,
            auto_post=True,
            send_photos=True
        )
        
        channel = create_channel(db, channel_data)
        
        assert channel.id is not None
        assert channel.name == "Test Channel"
        assert channel.chat_id == "@testchannel"
        assert channel.template_id == template.id
        assert channel.is_active is True
        assert channel.auto_post is True
    
    def test_create_channel_duplicate_chat_id_fails(self):
        """Test that creating channel with duplicate chat_id fails"""
        db = self.test_db
        
        # Create first channel
        channel_data1 = TelegramChannelCreate(
            name="Channel 1",
            chat_id="@duplicate",
            description="First channel"
        )
        create_channel(db, channel_data1)
        
        # Try to create second channel with same chat_id
        channel_data2 = TelegramChannelCreate(
            name="Channel 2",
            chat_id="@duplicate",
            description="Second channel"
        )
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            create_channel(db, channel_data2)
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_channel_invalid_template_fails(self):
        """Test creating channel with non-existent template fails"""
        db = self.test_db
        
        channel_data = TelegramChannelCreate(
            name="Test Channel",
            chat_id="@testchannel",
            template_id=999  # Non-existent template
        )
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            create_channel(db, channel_data)
        
        assert "Template not found" in str(exc_info.value)
    
    def test_get_channel_by_id(self):
        """Test retrieving channel by ID"""
        db = self.test_db
        
        # Create channel
        channel_data = TelegramChannelCreate(
            name="Test Channel",
            chat_id="@testchannel"
        )
        created_channel = create_channel(db, channel_data)
        
        # Retrieve channel
        retrieved_channel = get_channel_by_id(db, created_channel.id)
        
        assert retrieved_channel is not None
        assert retrieved_channel.id == created_channel.id
        assert retrieved_channel.name == "Test Channel"


class TestTelegramPostService:
    """Test telegram post service functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database and sample data"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        yield
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def create_test_product(self, db: Session) -> Product:
        """Helper to create test product"""
        product = Product(
            product_url="https://example.com/test-product",
            name="Test Product",
            sku="TEST-001",
            price=99.99,
            currency="USD",
            availability="In Stock"
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    
    def create_test_channel(self, db: Session, template_id: Optional[int] = None) -> TelegramChannel:
        """Helper to create test channel"""
        channel_data = TelegramChannelCreate(
            name="Test Channel",
            chat_id="@testchannel",
            template_id=template_id,
            is_active=True,
            auto_post=False,
            send_photos=True
        )
        return create_channel(db, channel_data)
    
    def create_test_template(self, db: Session) -> MessageTemplate:
        """Helper to create test template"""
        template_data = MessageTemplateCreate(
            name="Test Template",
            template_content="📦 Product: {product_name}\n💰 Price: {product_price} {product_currency}",
            is_active=True
        )
        return create_template(db, template_data)
    
    @pytest.mark.asyncio
    async def test_preview_post_with_custom_template(self):
        """Test post preview with custom template"""
        db = self.test_db
        product = self.create_test_product(db)
        channel = self.create_test_channel(db)
        
        service = TelegramPostService()
        
        preview = await service.preview_post(
            db=db,
            product_id=product.id,
            channel_id=channel.id,
            template_content="Custom: {product_name} costs {product_price}"
        )
        
        assert "Custom: Test Product costs 99.99" in preview["rendered_content"]
        assert preview["product_name"] == "Test Product"
        assert preview["channel_name"] == "Test Channel"
        assert preview["will_send_photos"] is True
    
    @pytest.mark.asyncio
    async def test_preview_post_with_channel_template(self):
        """Test post preview using channel's default template"""
        db = self.test_db
        template = self.create_test_template(db)
        product = self.create_test_product(db)
        channel = self.create_test_channel(db, template_id=template.id)
        
        service = TelegramPostService()
        
        preview = await service.preview_post(
            db=db,
            product_id=product.id,
            channel_id=channel.id
        )
        
        assert "📦 Product: Test Product" in preview["rendered_content"]
        assert "💰 Price: 99.99 USD" in preview["rendered_content"]
        assert preview["template_used"] == template.template_content
    
    @pytest.mark.asyncio
    async def test_preview_post_invalid_product(self):
        """Test preview with non-existent product"""
        db = self.test_db
        service = TelegramPostService()
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            await service.preview_post(db=db, product_id=999)
        
        assert "Product not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('services.telegram_post_service.telegram_service')
    async def test_send_post_service_disabled(self, mock_telegram_service):
        """Test sending post with disabled telegram service"""
        mock_telegram_service.is_enabled.return_value = False
        
        db = self.test_db
        product = self.create_test_product(db)
        channel = self.create_test_channel(db)
        
        service = TelegramPostService()
        
        from exceptions.base import ValidationException
        with pytest.raises(ValidationException) as exc_info:
            await service.send_post(
                db=db,
                product_id=product.id,
                channel_ids=[channel.id]
            )
        
        assert "disabled" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('services.telegram_post_service.telegram_service')
    async def test_send_post_success(self, mock_telegram_service):
        """Test successful post sending"""
        # Mock telegram service
        mock_telegram_service.is_enabled.return_value = True
        mock_telegram_service.send_message = AsyncMock(return_value={
            "ok": True,
            "result": {"message_id": 123}
        })
        
        db = self.test_db
        product = self.create_test_product(db)
        channel = self.create_test_channel(db)
        
        service = TelegramPostService()
        
        # Mock the internal method to avoid actual telegram sending
        with patch.object(service, '_send_post_to_telegram', new_callable=AsyncMock) as mock_send:
            result = await service.send_post(
                db=db,
                product_id=product.id,
                channel_ids=[channel.id],
                template_content="Test: {product_name}"
            )
        
        assert result["success_count"] == 1
        assert result["failed_count"] == 0
        assert len(result["posts_created"]) == 1
        assert len(result["errors"]) == 0


class TestTelegramAPI:
    """Test telegram API endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        
        # Override dependency injection for isolated testing
        def override_get_db():
            yield self.test_db
        app.dependency_overrides[get_db] = override_get_db
        
        self.client = TestClient(app)
        
        # Create test data
        db = self.test_db
        
        # Create template
        template_data = MessageTemplateCreate(
            name="API Test Template",
            template_content="API Test: {product_name}",
            is_active=True
        )
        self.template = create_template(db, template_data)
        
        # Create product
        product = Product(
            product_url="https://example.com/api-test-product",
            name="API Test Product",
            sku="API-001",
            price=49.99,
            currency="USD"
        )
        db.add(product)
        db.commit()
        self.test_product_id = product.id
        
        yield
        
        # Cleanup
        app.dependency_overrides.clear()
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
    
    def test_create_channel_api(self):
        """Test creating channel via API"""
        channel_data = {
            "name": "API Channel",
            "chat_id": "@apichannel",
            "description": "Created via API",
            "template_id": self.template.id,
            "is_active": True,
            "auto_post": False,
            "send_photos": True
        }
        
        response = self.client.post("/api/v1/telegram/channels", json=channel_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "API Channel"
        assert data["data"]["chat_id"] == "@apichannel"
        assert data["data"]["template_id"] == self.template.id
    
    def test_get_channels_list_api(self):
        """Test getting channels list via API"""
        # Create a channel first
        channel_data = {
            "name": "List Test Channel",
            "chat_id": "@listtestchannel",
            "is_active": True
        }
        self.client.post("/api/v1/telegram/channels", json=channel_data)
        
        # Get channels list
        response = self.client.get("/api/v1/telegram/channels")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert data["pagination"]["total"] > 0
    
    def test_preview_post_api(self):
        """Test post preview via API"""
        # Create channel first
        channel_data = {
            "name": "Preview Channel",
            "chat_id": "@previewchannel",
            "template_id": self.template.id
        }
        channel_response = self.client.post("/api/v1/telegram/channels", json=channel_data)
        channel_id = channel_response.json()["data"]["id"]
        
        # Preview post
        preview_data = {
            "product_id": self.test_product_id,
            "channel_id": channel_id
        }
        
        response = self.client.post("/api/v1/telegram/posts/preview", json=preview_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "rendered_content" in data
        assert "API Test Product" in data["rendered_content"]
        assert data["channel_name"] == "Preview Channel"
    
    @patch('api.routers.telegram.telegram_service')
    def test_channel_test_api(self, mock_telegram_service):
        """Test channel connection testing via API"""
        mock_telegram_service.is_enabled.return_value = True
        mock_telegram_service.get_chat_info = AsyncMock(return_value={
            "ok": True,
            "result": {"id": 123, "title": "Test Chat"}
        })
        
        test_data = {"chat_id": "@testchat"}
        
        response = self.client.post("/api/v1/telegram/channels/test", json=test_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["chat_info"]["id"] == 123
    
    def test_get_telegram_stats_api(self):
        """Test getting telegram statistics via API"""
        response = self.client.get("/api/v1/telegram/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_channels" in data
        assert "active_channels" in data
        assert "total_posts" in data
        assert "posts_sent" in data
    
    def test_get_service_status_api(self):
        """Test getting telegram service status via API"""
        response = self.client.get("/api/v1/telegram/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "service_enabled" in data["data"]
        assert "bot_token_configured" in data["data"]


class TestTelegramBulkPostIntegration:
    """Integration tests for bulk posting functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Set up test database for each test"""
        # Create isolated test database
        self.test_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.test_engine)
        
        # Create session
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        self.test_db = TestingSessionLocal()
        
        # Override database dependency
        def override_get_db():
            yield self.test_db
            
        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        
        yield
        
        # Cleanup
        self.test_db.close()
        Base.metadata.drop_all(bind=self.test_engine)
        app.dependency_overrides.clear()
    
    def create_test_products(self, count: int = 3, posted_count: int = 1):
        """Create test products with some posted and some unposted"""
        products = []
        
        for i in range(count):
            product = Product(
                name=f"Test Product {i+1}",
                product_url=f"https://example.com/product{i+1}",
                sku=f"SKU{i+1}",
                price=99.99,
                currency="USD",
                availability="In Stock",
                color="Red",
                composition="Cotton",
                item="Dress",
                comment="Test product",
                telegram_posted_at=None if i >= posted_count else datetime.utcnow()
            )
            self.test_db.add(product)
            products.append(product)
        
        self.test_db.commit()
        return products
    
    def create_test_channel(self, auto_post: bool = True, is_active: bool = True):
        """Create a test telegram channel"""
        channel_data = TelegramChannelCreate(
            name="Test Channel",
            chat_id="@testchannel",
            auto_post=auto_post,
            is_active=is_active,
            send_photos=True,
            disable_notification=False,
            disable_web_page_preview=True
        )
        
        channel = create_channel(self.test_db, channel_data)
        self.test_db.commit()
        return channel
    
    @patch('api.routers.telegram.telegram_service')
    @patch('api.routers.telegram.telegram_post_service')
    def test_get_unposted_count_integration(self, mock_post_service, mock_telegram_service):
        """Test getting unposted products count via API"""
        # Create test products - 2 unposted, 1 posted
        self.create_test_products(count=3, posted_count=1)
        
        response = self.client.get("/api/v1/telegram/unposted-count")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["unposted_count"] == 2
        assert "2 unposted products" in data["message"]
    
    def test_get_unposted_count_empty(self):
        """Test getting unposted count when all products are posted"""
        # Create products that are all posted
        self.create_test_products(count=2, posted_count=2)
        
        response = self.client.get("/api/v1/telegram/unposted-count")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["unposted_count"] == 0
        assert "0 unposted products" in data["message"]
    
    @patch('api.routers.telegram.telegram_service')
    @patch('api.routers.telegram.telegram_post_service')
    def test_bulk_post_integration_success(self, mock_post_service, mock_telegram_service):
        """Test complete bulk posting workflow"""
        # Setup mocks
        mock_telegram_service.is_enabled.return_value = True
        mock_post_service.send_post = AsyncMock(return_value={
            "posts_created": [MagicMock()],
            "success_count": 1,
            "failed_count": 0,
            "errors": []
        })
        
        # Create test data
        products = self.create_test_products(count=3, posted_count=1)  # 2 unposted
        channel = self.create_test_channel()
        
        # Execute bulk post
        response = self.client.post(f"/api/v1/telegram/bulk-post-unposted?channel_ids={channel.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_products"] == 2
        assert data["data"]["posted_count"] == 2  # Both products posted successfully
        assert data["data"]["failed_count"] == 0
        assert data["data"]["channels_used"] == 1
        assert len(data["data"]["results"]) == 2
        
        # Verify each result
        for result in data["data"]["results"]:
            assert result["success"] is True
            assert result["posts_created"] == 1
            assert result["errors"] == []
    
    @patch('api.routers.telegram.telegram_service')
    def test_bulk_post_no_unposted_products(self, mock_telegram_service):
        """Test bulk posting when no unposted products exist"""
        mock_telegram_service.is_enabled.return_value = True
        
        # All products are posted
        self.create_test_products(count=2, posted_count=2)
        
        response = self.client.post("/api/v1/telegram/bulk-post-unposted")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_products"] == 0
        assert data["message"] == "No unposted products found"
    
    @patch('api.routers.telegram.telegram_service')
    def test_bulk_post_no_active_channels(self, mock_telegram_service):
        """Test bulk posting when no auto-post channels exist"""
        mock_telegram_service.is_enabled.return_value = True
        
        # Create products and inactive channel
        self.create_test_products(count=2, posted_count=0)
        self.create_test_channel(auto_post=False)  # Not auto-post
        
        response = self.client.post("/api/v1/telegram/bulk-post-unposted")
        assert response.status_code == 400
        assert "No active channels found" in response.json()["error"]["message"]
    
    @patch('api.routers.telegram.telegram_service')
    def test_bulk_post_service_disabled(self, mock_telegram_service):
        """Test bulk posting when telegram service is disabled"""
        mock_telegram_service.is_enabled.return_value = False
        
        response = self.client.post("/api/v1/telegram/bulk-post-unposted")
        assert response.status_code == 400
        assert "Telegram service is disabled" in response.json()["error"]["message"]
    
    @patch('api.routers.telegram.telegram_service')
    @patch('api.routers.telegram.telegram_post_service')
    def test_bulk_post_with_failures(self, mock_post_service, mock_telegram_service):
        """Test bulk posting with some failures"""
        mock_telegram_service.is_enabled.return_value = True
        
        # Mock post service to fail for product 2
        def mock_send_post(*args, **kwargs):
            product_id = kwargs.get('product_id', 0)
            if product_id == 2:  # Fail for second product
                raise Exception("Network error")
            return {
                "posts_created": [MagicMock()],
                "success_count": 1,
                "failed_count": 0,
                "errors": []
            }
        
        mock_post_service.send_post = AsyncMock(side_effect=mock_send_post)
        
        # Create test data
        products = self.create_test_products(count=3, posted_count=1)  # 2 unposted
        channel = self.create_test_channel()
        
        # Execute bulk post
        response = self.client.post(f"/api/v1/telegram/bulk-post-unposted?channel_ids={channel.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_products"] == 2
        assert data["data"]["posted_count"] == 1  # One success
        assert data["data"]["failed_count"] == 1   # One failure
        
        # Check results details
        results = data["data"]["results"]
        success_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        assert len(success_results) == 1
        assert len(failed_results) == 1
        assert "Network error" in failed_results[0]["error"]
    
    @patch('api.routers.telegram.telegram_service')
    @patch('api.routers.telegram.telegram_post_service')
    def test_bulk_post_with_limit(self, mock_post_service, mock_telegram_service):
        """Test bulk posting with limit parameter"""
        mock_telegram_service.is_enabled.return_value = True
        mock_post_service.send_post = AsyncMock(return_value={
            "posts_created": [MagicMock()],
            "success_count": 1,
            "failed_count": 0,
            "errors": []
        })
        
        # Create 5 unposted products
        self.create_test_products(count=5, posted_count=0)
        channel = self.create_test_channel()
        
        # Execute bulk post with limit of 2
        response = self.client.post(f"/api/v1/telegram/bulk-post-unposted?channel_ids={channel.id}&limit=2")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_products"] == 2  # Limited to 2
        assert data["data"]["posted_count"] == 2
        assert data["data"]["failed_count"] == 0
    
    def test_database_query_ordering(self):
        """Test that unposted products are returned in creation order"""
        from crud.product import get_products_not_posted_to_telegram
        import time
        
        # Create products with slight delays to ensure different creation times
        product1 = Product(
            name="First Product",
            product_url="https://example.com/first",
            sku="SKU1",
            price=99.99
        )
        self.test_db.add(product1)
        self.test_db.commit()
        
        time.sleep(0.001)  # Small delay
        
        product2 = Product(
            name="Second Product", 
            product_url="https://example.com/second",
            sku="SKU2",
            price=99.99
        )
        self.test_db.add(product2)
        self.test_db.commit()
        
        # Get unposted products
        unposted = get_products_not_posted_to_telegram(self.test_db)
        
        # Should be ordered by creation time (oldest first)
        assert len(unposted) == 2
        assert unposted[0].name == "First Product"
        assert unposted[1].name == "Second Product"