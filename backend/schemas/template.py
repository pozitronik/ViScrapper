from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class MessageTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    template_content: str = Field(..., min_length=1, description="Template content with placeholders")
    is_active: bool = Field(True, description="Whether the template is active")
    
    # Image combination settings
    combine_images: bool = Field(False, description="Combine all product images into one image")
    
    # Image optimization settings  
    optimize_images: bool = Field(True, description="Enable image optimization (compression/resizing)")
    max_file_size_kb: int = Field(500, ge=50, le=5000, description="Maximum file size in KB (50-5000)")
    max_width: int = Field(1920, ge=200, le=4000, description="Maximum image width in pixels (200-4000)")
    max_height: int = Field(1080, ge=200, le=4000, description="Maximum image height in pixels (200-4000)")
    compression_quality: int = Field(80, ge=10, le=100, description="JPEG compression quality percentage (10-100)")


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    template_content: Optional[str] = Field(None, min_length=1, description="Template content with placeholders")
    is_active: Optional[bool] = Field(None, description="Whether the template is active")
    
    # Image combination settings
    combine_images: Optional[bool] = Field(None, description="Combine all product images into one image")
    
    # Image optimization settings  
    optimize_images: Optional[bool] = Field(None, description="Enable image optimization (compression/resizing)")
    max_file_size_kb: Optional[int] = Field(None, ge=50, le=5000, description="Maximum file size in KB (50-5000)")
    max_width: Optional[int] = Field(None, ge=200, le=4000, description="Maximum image width in pixels (200-4000)")
    max_height: Optional[int] = Field(None, ge=200, le=4000, description="Maximum image height in pixels (200-4000)")
    compression_quality: Optional[int] = Field(None, ge=10, le=100, description="JPEG compression quality percentage (10-100)")


class MessageTemplate(MessageTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TemplatePreviewRequest(BaseModel):
    template_content: str = Field(..., description="Template content to preview")
    product_id: int = Field(..., ge=1, description="Product ID to use for preview")


class TemplatePreviewResponse(BaseModel):
    rendered_content: str = Field(..., description="Template content with placeholders replaced")
    available_placeholders: list[str] = Field(..., description="List of available placeholder variables")


class TemplateRenderRequest(BaseModel):
    template_id: int = Field(..., ge=1, description="Template ID to render")
    product_id: int = Field(..., ge=1, description="Product ID to use for rendering")


class TemplateRenderResponse(BaseModel):
    template_name: str = Field(..., description="Name of the template")
    rendered_content: str = Field(..., description="Template content with placeholders replaced")
    product_name: str = Field(..., description="Name of the product used")
    product_url: str = Field(..., description="URL of the product used")
