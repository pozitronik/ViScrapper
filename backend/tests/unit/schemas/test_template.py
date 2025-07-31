"""
Comprehensive unit tests for template schemas.

This module contains extensive tests for all template-related Pydantic schemas including
MessageTemplateBase, MessageTemplateCreate, MessageTemplateUpdate, MessageTemplate,
TemplatePreviewRequest, TemplatePreviewResponse, TemplateRenderRequest, and TemplateRenderResponse.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from schemas.template import (
    MessageTemplateBase, MessageTemplateCreate, MessageTemplateUpdate, MessageTemplate,
    TemplatePreviewRequest, TemplatePreviewResponse,
    TemplateRenderRequest, TemplateRenderResponse
)


class TestMessageTemplateBase:
    """Test suite for MessageTemplateBase schema."""

    def test_message_template_base_minimal(self):
        """Test MessageTemplateBase with minimal required fields."""
        template = MessageTemplateBase(
            name="Test Template",
            template_content="Hello {product_name}!"
        )
        
        assert template.name == "Test Template"
        assert template.description is None
        assert template.template_content == "Hello {product_name}!"
        assert template.is_active is True

    def test_message_template_base_full(self):
        """Test MessageTemplateBase with all fields."""
        template = MessageTemplateBase(
            name="Full Template",
            description="A complete template for testing",
            template_content="Product: {product_name}\nPrice: {price}\nURL: {product_url}",
            is_active=False
        )
        
        assert template.name == "Full Template"
        assert template.description == "A complete template for testing"
        assert template.template_content == "Product: {product_name}\nPrice: {price}\nURL: {product_url}"
        assert template.is_active is False

    def test_message_template_base_name_validation(self):
        """Test name field validation."""
        # Valid name
        template = MessageTemplateBase(
            name="Valid Name",
            template_content="Content"
        )
        assert template.name == "Valid Name"
        
        # Empty name should fail
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(name="", template_content="Content")
        assert "at least 1 character" in str(exc_info.value)
        
        # Too long name should fail
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(name=long_name, template_content="Content")
        assert "at most 100 characters" in str(exc_info.value)

    def test_message_template_base_description_validation(self):
        """Test description field validation."""
        # Valid description
        template = MessageTemplateBase(
            name="Test",
            template_content="Content",
            description="A valid description"
        )
        assert template.description == "A valid description"
        
        # None description is valid
        template2 = MessageTemplateBase(
            name="Test",
            template_content="Content",
            description=None
        )
        assert template2.description is None
        
        # Too long description should fail
        long_desc = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(
                name="Test",
                template_content="Content",
                description=long_desc
            )
        assert "at most 500 characters" in str(exc_info.value)

    def test_message_template_base_template_content_validation(self):
        """Test template_content field validation."""
        # Valid content
        template = MessageTemplateBase(
            name="Test",
            template_content="Valid content with {placeholder}"
        )
        assert template.template_content == "Valid content with {placeholder}"
        
        # Empty content should fail
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(name="Test", template_content="")
        assert "at least 1 character" in str(exc_info.value)

    def test_message_template_base_boolean_conversion(self):
        """Test is_active boolean field conversion."""
        # Boolean values
        template1 = MessageTemplateBase(
            name="Test",
            template_content="Content",
            is_active=True
        )
        assert template1.is_active is True
        
        template2 = MessageTemplateBase(
            name="Test",
            template_content="Content",
            is_active=False
        )
        assert template2.is_active is False
        
        # Truthy/falsy values
        template3 = MessageTemplateBase(
            name="Test",
            template_content="Content",
            is_active=1
        )
        assert template3.is_active is True
        
        template4 = MessageTemplateBase(
            name="Test",
            template_content="Content",
            is_active=0
        )
        assert template4.is_active is False

    def test_message_template_base_serialization(self):
        """Test MessageTemplateBase JSON serialization."""
        template = MessageTemplateBase(
            name="Serialize Test",
            description="Test description",
            template_content="Content: {content}",
            is_active=True
        )
        
        json_data = template.model_dump()
        expected = {
            "name": "Serialize Test",
            "description": "Test description",
            "template_content": "Content: {content}",
            "is_active": True,
            "combine_images": False,
            "optimize_images": True,
            "max_file_size_kb": 500,
            "max_width": 1920,
            "max_height": 1080,
            "compression_quality": 80
        }
        
        assert json_data == expected

    def test_message_template_base_required_fields(self):
        """Test required field validation."""
        # Missing name
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(template_content="Content")
        assert "name" in str(exc_info.value)
        
        # Missing template_content
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateBase(name="Test")
        assert "template_content" in str(exc_info.value)


class TestMessageTemplateCreate:
    """Test suite for MessageTemplateCreate schema."""

    def test_message_template_create_inheritance(self):
        """Test that MessageTemplateCreate inherits from MessageTemplateBase."""
        template = MessageTemplateCreate(
            name="Create Test",
            template_content="Creating: {name}"
        )
        
        assert isinstance(template, MessageTemplateBase)
        assert template.name == "Create Test"
        assert template.template_content == "Creating: {name}"

    def test_message_template_create_functionality(self):
        """Test MessageTemplateCreate specific functionality."""
        template = MessageTemplateCreate(
            name="New Template",
            description="A newly created template",
            template_content="New: {product_name} - {price}",
            is_active=False
        )
        
        assert template.name == "New Template"
        assert template.description == "A newly created template"
        assert template.template_content == "New: {product_name} - {price}"
        assert template.is_active is False


class TestMessageTemplateUpdate:
    """Test suite for MessageTemplateUpdate schema."""

    def test_message_template_update_all_optional(self):
        """Test that all MessageTemplateUpdate fields are optional."""
        update = MessageTemplateUpdate()
        
        assert update.name is None
        assert update.description is None
        assert update.template_content is None
        assert update.is_active is None

    def test_message_template_update_partial(self):
        """Test MessageTemplateUpdate with partial data."""
        update = MessageTemplateUpdate(
            name="Updated Name",
            is_active=False
        )
        
        assert update.name == "Updated Name"
        assert update.is_active is False
        assert update.description is None
        assert update.template_content is None

    def test_message_template_update_full(self):
        """Test MessageTemplateUpdate with all fields."""
        update = MessageTemplateUpdate(
            name="Fully Updated",
            description="Updated description",
            template_content="Updated: {product_name}",
            is_active=True
        )
        
        assert update.name == "Fully Updated"
        assert update.description == "Updated description"
        assert update.template_content == "Updated: {product_name}"
        assert update.is_active is True

    def test_message_template_update_name_validation(self):
        """Test name validation in update schema."""
        # Valid name
        update = MessageTemplateUpdate(name="Valid Update Name")
        assert update.name == "Valid Update Name"
        
        # Empty name should fail (when provided)
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateUpdate(name="")
        assert "at least 1 character" in str(exc_info.value)
        
        # Too long name should fail
        long_name = "a" * 101
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateUpdate(name=long_name)
        assert "at most 100 characters" in str(exc_info.value)

    def test_message_template_update_description_validation(self):
        """Test description validation in update schema."""
        # Valid description
        update = MessageTemplateUpdate(description="Updated description")
        assert update.description == "Updated description"
        
        # None is valid
        update2 = MessageTemplateUpdate(description=None)
        assert update2.description is None
        
        # Too long description should fail
        long_desc = "a" * 501
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateUpdate(description=long_desc)
        assert "at most 500 characters" in str(exc_info.value)

    def test_message_template_update_content_validation(self):
        """Test template_content validation in update schema."""
        # Valid content
        update = MessageTemplateUpdate(template_content="Updated {content}")
        assert update.template_content == "Updated {content}"
        
        # Empty content should fail (when provided)
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplateUpdate(template_content="")
        assert "at least 1 character" in str(exc_info.value)


class TestMessageTemplate:
    """Test suite for MessageTemplate schema."""

    def test_message_template_full(self):
        """Test complete MessageTemplate schema."""
        now = datetime.now()
        
        template = MessageTemplate(
            id=1,
            name="Full Template",
            description="A complete template",
            template_content="Template: {name}",
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        assert template.id == 1
        assert template.name == "Full Template"
        assert template.description == "A complete template"
        assert template.template_content == "Template: {name}"
        assert template.is_active is True
        assert template.created_at == now
        assert template.updated_at == now
        assert template.deleted_at is None

    def test_message_template_with_deleted_at(self):
        """Test MessageTemplate with deleted_at timestamp."""
        now = datetime.now()
        deleted_time = datetime.now()
        
        template = MessageTemplate(
            id=2,
            name="Deleted Template",
            template_content="Deleted content",
            created_at=now,
            updated_at=now,
            deleted_at=deleted_time
        )
        
        assert template.id == 2
        assert template.deleted_at == deleted_time

    def test_message_template_inheritance(self):
        """Test that MessageTemplate inherits from MessageTemplateBase."""
        now = datetime.now()
        
        template = MessageTemplate(
            id=1,
            name="Inheritance Test",
            template_content="Testing inheritance",
            created_at=now,
            updated_at=now
        )
        
        assert isinstance(template, MessageTemplateBase)

    def test_message_template_required_fields(self):
        """Test MessageTemplate required fields."""
        now = datetime.now()
        
        # Missing id
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplate(
                name="Test",
                template_content="Content",
                created_at=now,
                updated_at=now
            )
        assert "id" in str(exc_info.value)
        
        # Missing created_at
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplate(
                id=1,
                name="Test",
                template_content="Content",
                updated_at=now
            )
        assert "created_at" in str(exc_info.value)
        
        # Missing updated_at
        with pytest.raises(ValidationError) as exc_info:
            MessageTemplate(
                id=1,
                name="Test",
                template_content="Content",
                created_at=now
            )
        assert "updated_at" in str(exc_info.value)

    def test_message_template_serialization(self):
        """Test MessageTemplate serialization."""
        now = datetime.now()
        
        template = MessageTemplate(
            id=1,
            name="Serialize Test",
            template_content="Serializing {data}",
            created_at=now,
            updated_at=now
        )
        
        json_data = template.model_dump()
        
        assert json_data["id"] == 1
        assert json_data["name"] == "Serialize Test"
        assert json_data["template_content"] == "Serializing {data}"
        assert "created_at" in json_data
        assert "updated_at" in json_data
        assert json_data["deleted_at"] is None


class TestTemplatePreviewRequest:
    """Test suite for TemplatePreviewRequest schema."""

    def test_template_preview_request_basic(self):
        """Test basic TemplatePreviewRequest."""
        request = TemplatePreviewRequest(
            template_content="Preview: {product_name}",
            product_id=42
        )
        
        assert request.template_content == "Preview: {product_name}"
        assert request.product_id == 42

    def test_template_preview_request_complex_content(self):
        """Test TemplatePreviewRequest with complex template content."""
        complex_content = """
        Product: {product_name}
        Price: {price} {currency}
        Available in: {color}
        Link: {product_url}
        """
        
        request = TemplatePreviewRequest(
            template_content=complex_content,
            product_id=123
        )
        
        assert request.template_content == complex_content
        assert request.product_id == 123

    def test_template_preview_request_product_id_validation(self):
        """Test product_id validation."""
        # Valid product ID
        request = TemplatePreviewRequest(
            template_content="Test",
            product_id=1
        )
        assert request.product_id == 1
        
        # Product ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewRequest(
                template_content="Test",
                product_id=0
            )
        assert "greater than or equal to 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewRequest(
                template_content="Test",
                product_id=-1
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_template_preview_request_required_fields(self):
        """Test required fields validation."""
        # Missing template_content
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewRequest(product_id=1)
        assert "template_content" in str(exc_info.value)
        
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewRequest(template_content="Test")
        assert "product_id" in str(exc_info.value)

    def test_template_preview_request_type_conversion(self):
        """Test type conversion for product_id."""
        # String that can be converted to int
        request = TemplatePreviewRequest(
            template_content="Test",
            product_id="42"
        )
        assert request.product_id == 42
        assert isinstance(request.product_id, int)


class TestTemplatePreviewResponse:
    """Test suite for TemplatePreviewResponse schema."""

    def test_template_preview_response_basic(self):
        """Test basic TemplatePreviewResponse."""
        response = TemplatePreviewResponse(
            rendered_content="Rendered: Test Product",
            available_placeholders=["product_name", "price", "currency"]
        )
        
        assert response.rendered_content == "Rendered: Test Product"
        assert response.available_placeholders == ["product_name", "price", "currency"]

    def test_template_preview_response_empty_placeholders(self):
        """Test TemplatePreviewResponse with empty placeholders."""
        response = TemplatePreviewResponse(
            rendered_content="No placeholders here",
            available_placeholders=[]
        )
        
        assert response.rendered_content == "No placeholders here"
        assert response.available_placeholders == []

    def test_template_preview_response_many_placeholders(self):
        """Test TemplatePreviewResponse with many placeholders."""
        placeholders = [
            "product_name", "product_url", "price", "currency", "color",
            "composition", "availability", "sku", "item", "comment"
        ]
        
        response = TemplatePreviewResponse(
            rendered_content="Complex rendered content",
            available_placeholders=placeholders
        )
        
        assert len(response.available_placeholders) == 10
        assert "product_name" in response.available_placeholders
        assert "comment" in response.available_placeholders

    def test_template_preview_response_required_fields(self):
        """Test required fields validation."""
        # Missing rendered_content
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewResponse(available_placeholders=["test"])
        assert "rendered_content" in str(exc_info.value)
        
        # Missing available_placeholders
        with pytest.raises(ValidationError) as exc_info:
            TemplatePreviewResponse(rendered_content="Test")
        assert "available_placeholders" in str(exc_info.value)

    def test_template_preview_response_serialization(self):
        """Test TemplatePreviewResponse serialization."""
        response = TemplatePreviewResponse(
            rendered_content="Serialization test",
            available_placeholders=["var1", "var2"]
        )
        
        json_data = response.model_dump()
        expected = {
            "rendered_content": "Serialization test",
            "available_placeholders": ["var1", "var2"]
        }
        
        assert json_data == expected


class TestTemplateRenderRequest:
    """Test suite for TemplateRenderRequest schema."""

    def test_template_render_request_basic(self):
        """Test basic TemplateRenderRequest."""
        request = TemplateRenderRequest(
            template_id=5,
            product_id=10
        )
        
        assert request.template_id == 5
        assert request.product_id == 10

    def test_template_render_request_id_validation(self):
        """Test ID field validation."""
        # Valid IDs
        request = TemplateRenderRequest(template_id=1, product_id=1)
        assert request.template_id == 1
        assert request.product_id == 1
        
        # Template ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderRequest(template_id=0, product_id=1)
        assert "greater than or equal to 1" in str(exc_info.value)
        
        # Product ID must be >= 1
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderRequest(template_id=1, product_id=0)
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_template_render_request_required_fields(self):
        """Test required fields validation."""
        # Missing template_id
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderRequest(product_id=1)
        assert "template_id" in str(exc_info.value)
        
        # Missing product_id
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderRequest(template_id=1)
        assert "product_id" in str(exc_info.value)

    def test_template_render_request_type_conversion(self):
        """Test type conversion for ID fields."""
        request = TemplateRenderRequest(
            template_id="5",
            product_id="10"
        )
        
        assert request.template_id == 5
        assert request.product_id == 10
        assert isinstance(request.template_id, int)
        assert isinstance(request.product_id, int)


class TestTemplateRenderResponse:
    """Test suite for TemplateRenderResponse schema."""

    def test_template_render_response_basic(self):
        """Test basic TemplateRenderResponse."""
        response = TemplateRenderResponse(
            template_name="Test Template",
            rendered_content="Rendered: Blue Shirt - $29.99",
            product_name="Blue Shirt",
            product_url="https://example.com/blue-shirt"
        )
        
        assert response.template_name == "Test Template"
        assert response.rendered_content == "Rendered: Blue Shirt - $29.99"
        assert response.product_name == "Blue Shirt"
        assert response.product_url == "https://example.com/blue-shirt"

    def test_template_render_response_complex(self):
        """Test TemplateRenderResponse with complex data."""
        complex_content = """
        Product: Premium Cotton T-Shirt
        Price: $34.99 USD
        Color: Navy Blue
        Available Now!
        Order at: https://shop.example.com/premium-tshirt
        """
        
        response = TemplateRenderResponse(
            template_name="Premium Product Template",
            rendered_content=complex_content,
            product_name="Premium Cotton T-Shirt",
            product_url="https://shop.example.com/premium-tshirt"
        )
        
        assert response.template_name == "Premium Product Template"
        assert "Premium Cotton T-Shirt" in response.rendered_content
        assert "$34.99 USD" in response.rendered_content

    def test_template_render_response_required_fields(self):
        """Test required fields validation."""
        # Missing template_name
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderResponse(
                rendered_content="Content",
                product_name="Product",
                product_url="https://example.com"
            )
        assert "template_name" in str(exc_info.value)
        
        # Missing rendered_content
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderResponse(
                template_name="Template",
                product_name="Product",
                product_url="https://example.com"
            )
        assert "rendered_content" in str(exc_info.value)
        
        # Missing product_name
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderResponse(
                template_name="Template",
                rendered_content="Content",
                product_url="https://example.com"
            )
        assert "product_name" in str(exc_info.value)
        
        # Missing product_url
        with pytest.raises(ValidationError) as exc_info:
            TemplateRenderResponse(
                template_name="Template",
                rendered_content="Content",
                product_name="Product"
            )
        assert "product_url" in str(exc_info.value)

    def test_template_render_response_serialization(self):
        """Test TemplateRenderResponse serialization."""
        response = TemplateRenderResponse(
            template_name="Serialization Test Template",
            rendered_content="Testing serialization",
            product_name="Test Product",
            product_url="https://example.com/test"
        )
        
        json_data = response.model_dump()
        expected = {
            "template_name": "Serialization Test Template",
            "rendered_content": "Testing serialization",
            "product_name": "Test Product",
            "product_url": "https://example.com/test"
        }
        
        assert json_data == expected


class TestTemplateSchemaIntegration:
    """Test integration between template schemas."""

    def test_template_lifecycle(self):
        """Test complete template lifecycle through different schemas."""
        # 1. Create template
        create_data = MessageTemplateCreate(
            name="Lifecycle Template",
            description="Testing complete lifecycle",
            template_content="Product: {product_name} - Price: {price}",
            is_active=True
        )
        
        # 2. Convert to full template (simulate database save)
        now = datetime.now()
        full_template = MessageTemplate(
            id=1,
            name=create_data.name,
            description=create_data.description,
            template_content=create_data.template_content,
            is_active=create_data.is_active,
            created_at=now,
            updated_at=now
        )
        
        # 3. Update template
        update_data = MessageTemplateUpdate(
            name="Updated Lifecycle Template",
            is_active=False
        )
        
        # 4. Preview template
        preview_request = TemplatePreviewRequest(
            template_content=full_template.template_content,
            product_id=1
        )
        
        # 5. Render template
        render_request = TemplateRenderRequest(
            template_id=full_template.id,
            product_id=1
        )
        
        # Verify all schemas work together
        assert full_template.name == "Lifecycle Template"
        assert update_data.name == "Updated Lifecycle Template"
        assert preview_request.product_id == 1
        assert render_request.template_id == 1

    def test_schema_validation_consistency(self):
        """Test that validation is consistent across schemas."""
        # Name validation should be consistent
        valid_name = "Valid Template Name"
        invalid_name = ""
        
        # Should work in base schema
        MessageTemplateBase(name=valid_name, template_content="Content")
        
        # Should work in create schema
        MessageTemplateCreate(name=valid_name, template_content="Content")
        
        # Should fail in base schema
        with pytest.raises(ValidationError):
            MessageTemplateBase(name=invalid_name, template_content="Content")
        
        # Should fail in update schema (when provided)
        with pytest.raises(ValidationError):
            MessageTemplateUpdate(name=invalid_name)

    def test_data_flow_between_schemas(self):
        """Test data flow between different template schemas."""
        # Start with create schema
        create_schema = MessageTemplateCreate(
            name="Flow Test",
            template_content="Testing {product_name}",
            description="Flow test description"
        )
        
        # Convert to dict and back to verify data integrity
        create_data = create_schema.model_dump()
        
        # Create full template from the data
        now = datetime.now()
        full_template = MessageTemplate(
            id=1,
            created_at=now,
            updated_at=now,
            **create_data
        )
        
        # Create update from original data
        update_schema = MessageTemplateUpdate(
            name=create_schema.name + " - Updated",
            is_active=False
        )
        
        # Verify data consistency
        assert full_template.name == create_schema.name
        assert full_template.template_content == create_schema.template_content
        assert full_template.description == create_schema.description
        assert update_schema.name == "Flow Test - Updated"

    def test_error_handling_across_schemas(self):
        """Test error handling consistency across template schemas."""
        # Test that similar validation errors occur across schemas
        long_name = "a" * 101
        
        # Should fail in base schema  
        with pytest.raises(ValidationError) as base_exc:
            MessageTemplateBase(name=long_name, template_content="Content")
        
        # Should fail in create schema
        with pytest.raises(ValidationError) as create_exc:
            MessageTemplateCreate(name=long_name, template_content="Content")
        
        # Should fail in update schema
        with pytest.raises(ValidationError) as update_exc:
            MessageTemplateUpdate(name=long_name)
        
        # Error messages should be similar
        assert "100 characters" in str(base_exc.value)
        assert "100 characters" in str(create_exc.value)
        assert "100 characters" in str(update_exc.value)