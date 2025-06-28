from pydantic import BaseModel, HttpUrl, computed_field, ConfigDict
from typing import List, Optional
from datetime import datetime
import os


class ImageBase(BaseModel):
    url: str


class ImageCreate(ImageBase):
    pass


class Image(ImageBase):
    id: int
    product_id: int

    model_config = ConfigDict(from_attributes=True)


class SizeBase(BaseModel):
    name: str


class SizeCreate(SizeBase):
    pass


class Size(SizeBase):
    id: int
    product_id: int

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    product_url: HttpUrl
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    color: Optional[str] = None
    composition: Optional[str] = None
    item: Optional[str] = None
    comment: Optional[str] = None


class ProductCreate(ProductBase):
    all_image_urls: Optional[List[str]] = []
    available_sizes: Optional[List[str]] = []


class ProductUpdate(BaseModel):
    """Schema for updating products - all fields are optional."""
    product_url: Optional[HttpUrl] = None
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    availability: Optional[str] = None
    color: Optional[str] = None
    composition: Optional[str] = None
    item: Optional[str] = None
    comment: Optional[str] = None


class Product(ProductBase):
    id: int
    created_at: datetime
    telegram_posted_at: Optional[datetime] = None
    images: List[Image] = []
    sizes: List[Size] = []

    @computed_field
    @property
    def sell_price(self) -> Optional[float]:
        """Calculate sell price using PRICE_MULTIPLIER environment variable"""
        if self.price is None:
            return None
        
        try:
            multiplier = float(os.getenv('PRICE_MULTIPLIER', '1.0'))
            return round(self.price * multiplier, 2)
        except (ValueError, TypeError):
            return None

    model_config = ConfigDict(from_attributes=True)
