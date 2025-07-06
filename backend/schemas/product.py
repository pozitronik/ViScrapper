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
    sku: str  # SKU - единственный обязательный идентификатор
    product_url: Optional[HttpUrl] = None  # URL только для хранения
    name: Optional[str] = None
    price: Optional[float] = None
    selling_price: Optional[float] = None
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
    """Schema for updating products - all fields are optional. SKU cannot be changed."""
    product_url: Optional[HttpUrl] = None
    name: Optional[str] = None
    # sku excluded - SKU cannot be updated as it's the primary identifier
    price: Optional[float] = None
    selling_price: Optional[float] = None
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
    deleted_at: Optional[datetime] = None
    images: List[Image] = []
    sizes: List[Size] = []

    @computed_field
    def sell_price(self) -> Optional[float]:
        """Calculate sell price using manual selling_price if set, otherwise PRICE_MULTIPLIER with optional rounding"""
        # If manual selling_price is set, use it
        if self.selling_price is not None:
            return self._apply_price_rounding(self.selling_price)
        
        # Otherwise use price with multiplier
        if self.price is None:
            return None

        try:
            multiplier = float(os.getenv('PRICE_MULTIPLIER', '1.0'))
            calculated_price = self.price * multiplier
            return self._apply_price_rounding(calculated_price)
        except (ValueError, TypeError):
            return None
    
    def _apply_price_rounding(self, price: float) -> float:
        """Apply price rounding based on PRICE_ROUNDING_THRESHOLD"""
        try:
            threshold = float(os.getenv('PRICE_ROUNDING_THRESHOLD', '0.0'))
            
            # If threshold is 0 or negative, just round to 2 decimal places
            if threshold <= 0:
                return round(price, 2)
            
            # Check if the decimal part exceeds the threshold
            integer_part = int(price)
            decimal_part = price - integer_part
            
            if decimal_part > threshold:
                # Round up to the next integer
                return float(integer_part + 1)
            else:
                # Keep as is, just round to 2 decimal places
                return round(price, 2)
                
        except (ValueError, TypeError):
            # If threshold is invalid, just round to 2 decimal places
            return round(price, 2)

    model_config = ConfigDict(from_attributes=True)
