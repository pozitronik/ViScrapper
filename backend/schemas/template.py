from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class MessageTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    template_content: str = Field(..., min_length=1, description="Template content with placeholders")
    is_active: bool = Field(True, description="Whether the template is active")


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    template_content: Optional[str] = Field(None, min_length=1, description="Template content with placeholders")
    is_active: Optional[bool] = Field(None, description="Whether the template is active")


class MessageTemplate(MessageTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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