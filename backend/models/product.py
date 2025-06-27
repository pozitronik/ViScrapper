from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    product_url = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    sku = Column(String, unique=True, index=True)
    price = Column(Float)
    currency = Column(String)
    availability = Column(String)
    color = Column(String)
    composition = Column(String)
    item = Column(String)
    comment = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    telegram_posted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    images = relationship("Image", back_populates="product")
    sizes = relationship("Size", back_populates="product")


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    product = relationship("Product", back_populates="images")


class Size(Base):
    __tablename__ = "sizes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    product_id = Column(Integer, ForeignKey("products.id"))
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

    def __repr__(self):
        return f"<MessageTemplate(id={self.id}, name='{self.name}', active={self.is_active})>"
