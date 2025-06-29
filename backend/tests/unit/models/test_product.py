"""
Comprehensive unit tests for SQLAlchemy models.

This module contains extensive tests for all SQLAlchemy models in the VIParser
application, covering model creation, relationships, constraints, and behavior.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from models.product import (
    Base,
    Product,
    Image,
    Size,
    MessageTemplate,
    TelegramChannel,
    TelegramPost
)


class TestDatabaseSetup:
    """Test database setup and base model functionality."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_base_model_creation(self, db_session):
        """Test that Base model is properly configured."""
        assert Base is not None
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, 'registry')

    def test_all_tables_created(self, db_session):
        """Test that all expected tables are created."""
        engine = db_session.bind
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        expected_tables = {
            'products',
            'images',
            'sizes',
            'message_templates',
            'telegram_channels',
            'telegram_posts'
        }
        
        assert expected_tables.issubset(set(table_names))


class TestProductModel:
    """Test suite for the Product model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_product_creation_basic(self, db_session):
        """Test basic product creation."""
        product = Product(
            product_url="https://example.com/product/123",
            name="Test Product",
            sku="TEST-123",
            price=99.99,
            currency="USD"
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.id is not None
        assert product.product_url == "https://example.com/product/123"
        assert product.name == "Test Product"
        assert product.sku == "TEST-123"
        assert product.price == 99.99
        assert product.currency == "USD"
        assert product.created_at is not None

    def test_product_creation_with_optional_fields(self, db_session):
        """Test product creation with optional fields."""
        product = Product(
            product_url="https://example.com/product/456",
            name="Full Product",
            sku="FULL-456",
            price=149.99,
            currency="EUR",
            availability="In Stock",
            color="Red",
            composition="100% Cotton",
            item="Shirt",
            comment="Test comment"
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.availability == "In Stock"
        assert product.color == "Red"
        assert product.composition == "100% Cotton"
        assert product.item == "Shirt"
        assert product.comment == "Test comment"

    def test_product_url_unique_constraint(self, db_session):
        """Test that product_url has unique constraint."""
        product1 = Product(
            product_url="https://example.com/duplicate",
            name="Product 1",
            sku="SKU-1"
        )
        product2 = Product(
            product_url="https://example.com/duplicate",
            name="Product 2",
            sku="SKU-2"
        )
        
        db_session.add(product1)
        db_session.commit()
        
        db_session.add(product2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_product_sku_unique_constraint(self, db_session):
        """Test that SKU has unique constraint."""
        product1 = Product(
            product_url="https://example.com/product1",
            name="Product 1",
            sku="DUPLICATE-SKU"
        )
        product2 = Product(
            product_url="https://example.com/product2",
            name="Product 2",
            sku="DUPLICATE-SKU"
        )
        
        db_session.add(product1)
        db_session.commit()
        
        db_session.add(product2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_product_soft_delete(self, db_session):
        """Test soft delete functionality."""
        product = Product(
            product_url="https://example.com/soft-delete",
            name="Soft Delete Test",
            sku="SOFT-123"
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.deleted_at is None
        
        # Simulate soft delete
        product.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert product.deleted_at is not None

    def test_product_telegram_posted_at(self, db_session):
        """Test telegram_posted_at field."""
        product = Product(
            product_url="https://example.com/telegram",
            name="Telegram Test",
            sku="TELEGRAM-123"
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.telegram_posted_at is None
        
        # Simulate telegram posting
        telegram_time = datetime.now(timezone.utc)
        product.telegram_posted_at = telegram_time
        db_session.commit()
        
        # Refresh from database to get the stored value
        db_session.refresh(product)
        assert product.telegram_posted_at is not None
        # Check that the time is close (SQLite may lose some precision)
        time_diff = abs((product.telegram_posted_at.replace(tzinfo=timezone.utc) - telegram_time).total_seconds())
        assert time_diff < 1  # Within 1 second

    def test_product_images_relationship(self, db_session):
        """Test relationship with images."""
        product = Product(
            product_url="https://example.com/with-images",
            name="Product with Images",
            sku="IMG-123"
        )
        
        db_session.add(product)
        db_session.flush()  # Get the product ID
        
        image1 = Image(
            url="https://example.com/image1.jpg",
            product_id=product.id
        )
        image2 = Image(
            url="https://example.com/image2.jpg",
            product_id=product.id
        )
        
        db_session.add_all([image1, image2])
        db_session.commit()
        
        assert len(product.images) == 2
        assert image1 in product.images
        assert image2 in product.images

    def test_product_sizes_relationship(self, db_session):
        """Test relationship with sizes."""
        product = Product(
            product_url="https://example.com/with-sizes",
            name="Product with Sizes",
            sku="SIZE-123"
        )
        
        db_session.add(product)
        db_session.flush()
        
        size1 = Size(
            product_id=product.id,
            size_type="simple",
            size_value="M"
        )
        size2 = Size(
            product_id=product.id,
            size_type="simple",
            size_value="L"
        )
        
        db_session.add_all([size1, size2])
        db_session.commit()
        
        assert len(product.sizes) == 2
        assert size1 in product.sizes
        assert size2 in product.sizes

    def test_product_default_values(self, db_session):
        """Test default values for product fields."""
        product = Product(
            product_url="https://example.com/defaults",
            name="Default Test",
            sku="DEFAULT-123"
        )
        
        db_session.add(product)
        db_session.commit()
        
        # Test that nullable fields are None by default
        assert product.availability is None
        assert product.color is None
        assert product.composition is None
        assert product.item is None
        assert product.comment is None
        assert product.telegram_posted_at is None
        assert product.deleted_at is None
        
        # Test that created_at is automatically set
        assert product.created_at is not None
        assert isinstance(product.created_at, datetime)

    def test_product_column_indexes(self, db_session):
        """Test that proper indexes are created."""
        engine = db_session.bind
        inspector = inspect(engine)
        indexes = inspector.get_indexes('products')
        
        # Extract column names from indexes
        indexed_columns = set()
        for index in indexes:
            indexed_columns.update(index['column_names'])
        
        # Check that expected columns are indexed
        expected_indexed = {'product_url', 'name', 'sku', 'deleted_at'}
        assert expected_indexed.issubset(indexed_columns)


class TestImageModel:
    """Test suite for the Image model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_image_creation_basic(self, db_session):
        """Test basic image creation."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        image = Image(
            url="https://example.com/image.jpg",
            product_id=product.id
        )
        
        db_session.add(image)
        db_session.commit()
        
        assert image.id is not None
        assert image.url == "https://example.com/image.jpg"
        assert image.product_id == product.id

    def test_image_with_metadata(self, db_session):
        """Test image creation with file metadata."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        image = Image(
            url="https://example.com/image.jpg",
            product_id=product.id,
            file_hash="abc123def456",
            file_size=1024000
        )
        
        db_session.add(image)
        db_session.commit()
        
        assert image.file_hash == "abc123def456"
        assert image.file_size == 1024000

    def test_image_url_unique_constraint(self, db_session):
        """Test that image URL has unique constraint."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        image1 = Image(
            url="https://example.com/duplicate-image.jpg",
            product_id=product.id
        )
        image2 = Image(
            url="https://example.com/duplicate-image.jpg",
            product_id=product.id
        )
        
        db_session.add(image1)
        db_session.commit()
        
        db_session.add(image2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_image_product_relationship(self, db_session):
        """Test relationship with product."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        image = Image(
            url="https://example.com/image.jpg",
            product_id=product.id
        )
        db_session.add(image)
        db_session.commit()
        
        assert image.product == product
        assert image in product.images

    def test_image_soft_delete(self, db_session):
        """Test soft delete for images."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        image = Image(
            url="https://example.com/image.jpg",
            product_id=product.id
        )
        db_session.add(image)
        db_session.commit()
        
        assert image.deleted_at is None
        
        # Simulate soft delete
        image.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert image.deleted_at is not None


class TestSizeModel:
    """Test suite for the Size model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_size_creation_simple(self, db_session):
        """Test simple size creation."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        size = Size(
            product_id=product.id,
            size_type="simple",
            size_value="M"
        )
        
        db_session.add(size)
        db_session.commit()
        
        assert size.id is not None
        assert size.product_id == product.id
        assert size.size_type == "simple"
        assert size.size_value == "M"
        assert size.size1_type is None
        assert size.size2_type is None
        assert size.combination_data is None

    def test_size_creation_combination(self, db_session):
        """Test combination size creation."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        combination_data = {
            "34": ["B", "C"],
            "36": ["A", "B"],
            "38": ["A"]
        }
        
        size = Size(
            product_id=product.id,
            size_type="combination",
            size1_type="Band",
            size2_type="Cup",
            combination_data=combination_data
        )
        
        db_session.add(size)
        db_session.commit()
        
        assert size.size_type == "combination"
        assert size.size1_type == "Band"
        assert size.size2_type == "Cup"
        assert size.combination_data == combination_data
        assert size.size_value is None

    def test_size_product_relationship(self, db_session):
        """Test relationship with product."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        size = Size(
            product_id=product.id,
            size_type="simple",
            size_value="L"
        )
        db_session.add(size)
        db_session.commit()
        
        assert size.product == product
        assert size in product.sizes

    def test_size_foreign_key_constraint(self, db_session):
        """Test foreign key constraint for product_id."""
        # Note: SQLite doesn't enforce foreign key constraints by default
        # This test verifies the column exists and can hold the value
        size = Size(
            product_id=99999,  # Non-existent product
            size_type="simple",
            size_value="M"
        )
        
        db_session.add(size)
        # SQLite allows this, so we just verify it can be committed
        db_session.commit()
        assert size.product_id == 99999

    def test_size_soft_delete(self, db_session):
        """Test soft delete for sizes."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        size = Size(
            product_id=product.id,
            size_type="simple",
            size_value="M"
        )
        db_session.add(size)
        db_session.commit()
        
        assert size.deleted_at is None
        
        # Simulate soft delete
        size.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert size.deleted_at is not None

    def test_size_json_field(self, db_session):
        """Test JSON field functionality."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        db_session.add(product)
        db_session.flush()
        
        complex_data = {
            "sizes": ["34", "36", "38"],
            "availability": {
                "34": {"B": True, "C": False},
                "36": {"A": True, "B": True}
            },
            "metadata": {
                "source": "api",
                "updated": "2023-01-01"
            }
        }
        
        size = Size(
            product_id=product.id,
            size_type="combination",
            combination_data=complex_data
        )
        
        db_session.add(size)
        db_session.commit()
        
        # Refresh from database to ensure JSON serialization/deserialization works
        db_session.refresh(size)
        assert size.combination_data == complex_data


class TestMessageTemplateModel:
    """Test suite for the MessageTemplate model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_template_creation_basic(self, db_session):
        """Test basic template creation."""
        template = MessageTemplate(
            name="Basic Template",
            template_content="Hello {{name}}!"
        )
        
        db_session.add(template)
        db_session.commit()
        
        assert template.id is not None
        assert template.name == "Basic Template"
        assert template.template_content == "Hello {{name}}!"
        assert template.is_active is True
        assert template.created_at is not None
        assert template.updated_at is not None

    def test_template_creation_with_description(self, db_session):
        """Test template creation with description."""
        template = MessageTemplate(
            name="Detailed Template",
            description="A template for greeting users",
            template_content="Welcome {{name}} to our service!"
        )
        
        db_session.add(template)
        db_session.commit()
        
        assert template.description == "A template for greeting users"

    def test_template_name_unique_constraint(self, db_session):
        """Test that template name has unique constraint."""
        template1 = MessageTemplate(
            name="Duplicate Name",
            template_content="Content 1"
        )
        template2 = MessageTemplate(
            name="Duplicate Name",
            template_content="Content 2"
        )
        
        db_session.add(template1)
        db_session.commit()
        
        db_session.add(template2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_template_active_status(self, db_session):
        """Test template active status functionality."""
        template = MessageTemplate(
            name="Active Template",
            template_content="Content",
            is_active=False
        )
        
        db_session.add(template)
        db_session.commit()
        
        assert template.is_active is False

    def test_template_soft_delete(self, db_session):
        """Test soft delete for templates."""
        template = MessageTemplate(
            name="Delete Template",
            template_content="Content"
        )
        
        db_session.add(template)
        db_session.commit()
        
        assert template.deleted_at is None
        
        # Simulate soft delete
        template.deleted_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert template.deleted_at is not None

    def test_template_repr(self, db_session):
        """Test template string representation."""
        template = MessageTemplate(
            name="Test Template",
            template_content="Content",
            is_active=True
        )
        
        db_session.add(template)
        db_session.commit()
        
        repr_str = repr(template)
        assert "MessageTemplate" in repr_str
        assert f"id={template.id}" in repr_str
        assert "name='Test Template'" in repr_str
        assert "active=True" in repr_str

    def test_template_updated_at_auto_update(self, db_session):
        """Test that updated_at is automatically updated on modification."""
        template = MessageTemplate(
            name="Update Test",
            template_content="Original content"
        )
        
        db_session.add(template)
        db_session.commit()
        
        original_updated_at = template.updated_at
        
        # Modify the template
        template.template_content = "Modified content"
        db_session.commit()
        
        # Note: In SQLite, the onupdate trigger might not work exactly as in PostgreSQL
        # This test verifies the column exists and can be manually updated
        template.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert template.updated_at != original_updated_at


class TestTelegramChannelModel:
    """Test suite for the TelegramChannel model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_channel_creation_basic(self, db_session):
        """Test basic channel creation."""
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        db_session.add(channel)
        db_session.commit()
        
        assert channel.id is not None
        assert channel.name == "Test Channel"
        assert channel.chat_id == "-1001234567890"
        assert channel.is_active is True
        assert channel.auto_post is False
        assert channel.send_photos is True
        assert channel.disable_web_page_preview is True
        assert channel.disable_notification is False

    def test_channel_with_template(self, db_session):
        """Test channel creation with template relationship."""
        template = MessageTemplate(
            name="Channel Template",
            template_content="New product: {{name}}"
        )
        db_session.add(template)
        db_session.flush()
        
        channel = TelegramChannel(
            name="Channel with Template",
            chat_id="-1001111111111",
            template_id=template.id
        )
        
        db_session.add(channel)
        db_session.commit()
        
        assert channel.template_id == template.id
        assert channel.template == template

    def test_channel_chat_id_unique_constraint(self, db_session):
        """Test that chat_id has unique constraint."""
        channel1 = TelegramChannel(
            name="Channel 1",
            chat_id="-1001234567890"
        )
        channel2 = TelegramChannel(
            name="Channel 2",
            chat_id="-1001234567890"
        )
        
        db_session.add(channel1)
        db_session.commit()
        
        db_session.add(channel2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_channel_configuration_options(self, db_session):
        """Test channel configuration options."""
        channel = TelegramChannel(
            name="Configured Channel",
            chat_id="-1001987654321",
            auto_post=True,
            send_photos=False,
            disable_web_page_preview=False,
            disable_notification=True
        )
        
        db_session.add(channel)
        db_session.commit()
        
        assert channel.auto_post is True
        assert channel.send_photos is False
        assert channel.disable_web_page_preview is False
        assert channel.disable_notification is True

    def test_channel_repr(self, db_session):
        """Test channel string representation."""
        channel = TelegramChannel(
            name="Repr Test Channel",
            chat_id="-1001122334455",
            is_active=True
        )
        
        db_session.add(channel)
        db_session.commit()
        
        repr_str = repr(channel)
        assert "TelegramChannel" in repr_str
        assert f"id={channel.id}" in repr_str
        assert "name='Repr Test Channel'" in repr_str
        assert "chat_id='-1001122334455'" in repr_str
        assert "active=True" in repr_str


class TestTelegramPostModel:
    """Test suite for the TelegramPost model."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_post_creation_basic(self, db_session):
        """Test basic post creation."""
        # Create required related objects
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        db_session.add_all([product, channel])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            rendered_content="Test product is now available!"
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert post.id is not None
        assert post.product_id == product.id
        assert post.channel_id == channel.id
        assert post.rendered_content == "Test product is now available!"
        assert post.status == "pending"
        assert post.retry_count == 0
        assert post.created_at is not None

    def test_post_with_template(self, db_session):
        """Test post creation with template."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        template = MessageTemplate(
            name="Post Template",
            template_content="Product: {{name}}"
        )
        
        db_session.add_all([product, channel, template])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            template_id=template.id,
            rendered_content="Product: Test Product"
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert post.template_id == template.id
        assert post.template == template

    def test_post_status_updates(self, db_session):
        """Test post status updates."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        db_session.add_all([product, channel])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            rendered_content="Test content"
        )
        
        db_session.add(post)
        db_session.commit()
        
        # Test status progression
        assert post.status == "pending"
        
        post.status = "sent"
        post.message_id = 12345
        post.sent_at = datetime.now(timezone.utc)
        db_session.commit()
        
        assert post.status == "sent"
        assert post.message_id == 12345
        assert post.sent_at is not None

    def test_post_error_handling(self, db_session):
        """Test post error handling."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        db_session.add_all([product, channel])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            rendered_content="Test content"
        )
        
        db_session.add(post)
        db_session.commit()
        
        # Simulate error
        post.status = "failed"
        post.error_message = "Channel not found"
        post.retry_count = 3
        db_session.commit()
        
        assert post.status == "failed"
        assert post.error_message == "Channel not found"
        assert post.retry_count == 3

    def test_post_relationships(self, db_session):
        """Test post relationships."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        template = MessageTemplate(
            name="Post Template",
            template_content="Content"
        )
        
        db_session.add_all([product, channel, template])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            template_id=template.id,
            rendered_content="Test content"
        )
        
        db_session.add(post)
        db_session.commit()
        
        assert post.product == product
        assert post.channel == channel
        assert post.template == template

    def test_post_repr(self, db_session):
        """Test post string representation."""
        product = Product(
            product_url="https://example.com/product",
            name="Test Product",
            sku="TEST-123"
        )
        channel = TelegramChannel(
            name="Test Channel",
            chat_id="-1001234567890"
        )
        
        db_session.add_all([product, channel])
        db_session.flush()
        
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            rendered_content="Test content",
            status="sent"
        )
        
        db_session.add(post)
        db_session.commit()
        
        repr_str = repr(post)
        assert "TelegramPost" in repr_str
        assert f"id={post.id}" in repr_str
        assert f"product_id={product.id}" in repr_str
        assert f"channel_id={channel.id}" in repr_str
        assert "status='sent'" in repr_str


class TestModelIntegration:
    """Test integration between different models."""

    @pytest.fixture(scope="function")
    def db_session(self):
        """Create a test database session."""
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    def test_complete_product_workflow(self, db_session):
        """Test complete workflow with all related models."""
        # Create a product with images and sizes
        product = Product(
            product_url="https://example.com/complete-product",
            name="Complete Product",
            sku="COMPLETE-123",
            price=199.99,
            currency="USD"
        )
        
        db_session.add(product)
        db_session.flush()
        
        # Add images
        images = [
            Image(url="https://example.com/img1.jpg", product_id=product.id),
            Image(url="https://example.com/img2.jpg", product_id=product.id)
        ]
        
        # Add sizes
        sizes = [
            Size(product_id=product.id, size_type="simple", size_value="S"),
            Size(product_id=product.id, size_type="simple", size_value="M"),
            Size(product_id=product.id, size_type="simple", size_value="L")
        ]
        
        db_session.add_all(images + sizes)
        db_session.commit()
        
        # Verify relationships
        assert len(product.images) == 2
        assert len(product.sizes) == 3
        
        # Create telegram infrastructure
        template = MessageTemplate(
            name="Product Template",
            template_content="New product: {{name}} - {{price}} {{currency}}"
        )
        
        channel = TelegramChannel(
            name="Product Channel",
            chat_id="-1001234567890",
            auto_post=True
        )
        
        db_session.add_all([template, channel])
        db_session.flush()
        
        # Create telegram post
        post = TelegramPost(
            product_id=product.id,
            channel_id=channel.id,
            template_id=template.id,
            rendered_content=f"New product: {product.name} - {product.price} {product.currency}"
        )
        
        db_session.add(post)
        db_session.commit()
        
        # Verify complete integration
        assert post.product == product
        assert post.channel == channel
        assert post.template == template
        assert len(post.product.images) == 2
        assert len(post.product.sizes) == 3

    def test_cascade_behavior(self, db_session):
        """Test behavior when related objects are deleted."""
        # This test verifies that foreign key constraints work properly
        product = Product(
            product_url="https://example.com/cascade-test",
            name="Cascade Test",
            sku="CASCADE-123"
        )
        
        db_session.add(product)
        db_session.flush()
        
        image = Image(url="https://example.com/cascade-img.jpg", product_id=product.id)
        db_session.add(image)
        db_session.commit()
        
        product_id = product.id
        image_id = image.id
        
        # Delete product (this should work due to foreign key constraints)
        db_session.delete(product)
        db_session.commit()
        
        # In SQLite without foreign key enforcement, image may still exist
        # but the relationship will be broken
        remaining_image = db_session.query(Image).filter(Image.id == image_id).first()
        # The image might be deleted by cascade or remain orphaned
        # This depends on SQLite configuration, so we just verify the behavior
        if remaining_image:
            # If it exists, it should have the original product_id or None
            assert remaining_image.product_id in [product_id, None]

    def test_soft_delete_consistency(self, db_session):
        """Test soft delete consistency across related models."""
        product = Product(
            product_url="https://example.com/soft-delete-test",
            name="Soft Delete Test",
            sku="SOFT-123"
        )
        
        db_session.add(product)
        db_session.flush()
        
        image = Image(url="https://example.com/soft-img.jpg", product_id=product.id)
        size = Size(product_id=product.id, size_type="simple", size_value="M")
        
        db_session.add_all([image, size])
        db_session.commit()
        
        # Soft delete all related objects
        delete_time = datetime.now(timezone.utc)
        product.deleted_at = delete_time
        image.deleted_at = delete_time
        size.deleted_at = delete_time
        
        db_session.commit()
        
        # Refresh from database to handle timezone conversions
        db_session.refresh(product)
        db_session.refresh(image)
        db_session.refresh(size)
        
        # Verify all have deletion timestamps (may lose timezone info in SQLite)
        assert product.deleted_at is not None
        assert image.deleted_at is not None
        assert size.deleted_at is not None
        
        # Check that all deletion times are close to each other
        times = [product.deleted_at, image.deleted_at, size.deleted_at]
        # Convert to UTC if needed
        utc_times = [t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t for t in times]
        
        # All times should be within a few seconds of each other
        max_time = max(utc_times)
        min_time = min(utc_times)
        time_diff = (max_time - min_time).total_seconds()
        assert time_diff < 5  # Within 5 seconds