from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, Text, Boolean, JSON, and_, Index
from sqlalchemy.orm import relationship, declarative_base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase as Base
else:
    Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_url = Column(String, index=True)  # URL для хранения, не уникальный
    name = Column(String, index=True)
    sku = Column(String, index=True)  # Уникальность через составной constraint
    price = Column(Float)
    selling_price = Column(Float, nullable=True, comment="Manual override for selling price. If null, uses price modifier calculation")
    currency = Column(String)
    availability = Column(String)
    color = Column(String)
    composition = Column(String)
    item = Column(String)
    comment = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    telegram_posted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    images = relationship("Image", back_populates="product", primaryjoin="and_(Product.id == Image.product_id, Image.deleted_at.is_(None))")
    sizes = relationship("Size", back_populates="product", primaryjoin="and_(Product.id == Size.product_id, Size.deleted_at.is_(None))")

    __table_args__ = (
        # Составной уникальный индекс: (sku, deleted_at)
        # В production заменен на partial index через миграцию bd6cc0311453
        # Но оставлен здесь для совместимости при создании новых баз через create_all()
        Index('ix_products_sku_deleted_unique', 'sku', 'deleted_at', unique=True),
    )


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    file_hash = Column(String, nullable=True, index=True)  # SHA256 hash of image content
    file_size = Column(Integer, nullable=True)  # File size in bytes
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    product = relationship("Product", back_populates="images")


class Size(Base):
    __tablename__ = "sizes"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    size_type = Column(String, nullable=False)  # 'simple' or 'combination'
    size_value = Column(String, nullable=True)  # For simple sizes: the size value (e.g., "M", "L")
    size1_type = Column(String, nullable=True)  # For combinations: first size type (e.g., "Band")
    size2_type = Column(String, nullable=True)  # For combinations: second size type (e.g., "Cup")
    combination_data = Column(JSON, nullable=True)  # For combinations: {"34": ["B", "C"], "36": ["A"]}
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    product = relationship("Product", back_populates="sizes")


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    template_content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<MessageTemplate(id={self.id}, name='{self.name}', active={self.is_active})>"


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    chat_id = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    template_id = Column(Integer, ForeignKey("message_templates.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    auto_post = Column(Boolean, default=False, nullable=False)
    send_photos = Column(Boolean, default=True, nullable=False)
    disable_web_page_preview = Column(Boolean, default=True, nullable=False)
    disable_notification = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    template = relationship("MessageTemplate")

    def __repr__(self) -> str:
        return f"<TelegramChannel(id={self.id}, name='{self.name}', chat_id='{self.chat_id}', active={self.is_active})>"


class TelegramPost(Base):
    __tablename__ = "telegram_posts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("telegram_channels.id"), nullable=False)
    message_id = Column(Integer, nullable=True)  # Telegram message ID
    template_id = Column(Integer, ForeignKey("message_templates.id"), nullable=True)
    rendered_content = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending", nullable=False)  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    product = relationship("Product")
    channel = relationship("TelegramChannel")
    template = relationship("MessageTemplate")

    def __repr__(self) -> str:
        return f"<TelegramPost(id={self.id}, product_id={self.product_id}, channel_id={self.channel_id}, status='{self.status}')>"
