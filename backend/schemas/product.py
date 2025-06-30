from pydantic import BaseModel, HttpUrl, computed_field, ConfigDict
from typing import List, Optional, Dict, Any
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
    size_type: str  # 'simple' or 'combination'
    size_value: Optional[str] = None  # For simple sizes: the size value (e.g., "M", "L")
    size1_type: Optional[str] = None  # For combinations: first size type (e.g., "Band")
    size2_type: Optional[str] = None  # For combinations: second size type (e.g., "Cup") 
    combination_data: Optional[Dict[str, List[str]]] = None  # For combinations: {"34": ["B", "C"], "36": ["A"]}


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
    size_combinations: Optional[Dict[str, Any]] = None  # For dual size selectors: {"size1_type": "Band", "size2_type": "Cup", "combinations": {"34": ["B", "C"]}}


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
