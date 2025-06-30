"""
Comprehensive unit tests for templates API router.

This module contains tests for all template endpoints including listing,
creation, updates, deletion, restoration, preview, rendering, and validation.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from api.routers.templates import router
from database.session import get_db
from exceptions.base import ValidationException


@pytest.fixture
def test_app():
    """Create test FastAPI app with templates router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return Mock()


@pytest.fixture
def test_client(test_app, mock_db):
    """Create test client with mocked database dependency."""
    def mock_get_db():
        return mock_db
    
    test_app.dependency_overrides[get_db] = mock_get_db
    client = TestClient(test_app)
    yield client
    test_app.dependency_overrides.clear()


class TestTemplatesRouter:
    """Test suite for templates API router."""

    @patch('api.routers.templates.get_templates')
    @patch('api.routers.templates.get_template_count')
    def test_list_templates_success(self, mock_count, mock_get_templates, test_client, mock_db):
        """Test successful templates listing."""
        mock_template1 = Mock()
        mock_template1.id = 1
        mock_template1.name = "Template 1"
        mock_template1.description = "Test template 1"
        mock_template1.template_content = "Hello {product_name}"
        mock_template1.is_active = True
        mock_template1.created_at = "2023-01-01T00:00:00"
        mock_template1.updated_at = "2023-01-01T00:00:00"
        mock_template1.deleted_at = None
        
        mock_template2 = Mock()
        mock_template2.id = 2
        mock_template2.name = "Template 2"
        mock_template2.description = "Test template 2"
        mock_template2.template_content = "Welcome {customer_name}"
        mock_template2.is_active = True
        mock_template2.created_at = "2023-01-01T00:00:00"
        mock_template2.updated_at = "2023-01-01T00:00:00"
        mock_template2.deleted_at = None
        
        mock_templates = [mock_template1, mock_template2]
        mock_get_templates.return_value = mock_templates
        mock_count.return_value = 2
        
        response = test_client.get("/api/v1/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) == 2
        assert data["pagination"]["total"] == 2
        
        mock_get_templates.assert_called_once_with(
            mock_db, skip=0, limit=20, include_deleted=False, active_only=False
        )
        mock_count.assert_called_once_with(mock_db, include_deleted=False, active_only=False)

    @patch('api.routers.templates.get_templates')
    @patch('api.routers.templates.get_template_count')
    def test_list_templates_with_filters(self, mock_count, mock_get_templates, test_client, mock_db):
        """Test templates listing with filters."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.name = "Active Template"
        mock_template.description = "Active template"
        mock_template.template_content = "Hello {product_name}"
        mock_template.is_active = True
        mock_template.created_at = "2023-01-01T00:00:00"
        mock_template.updated_at = "2023-01-01T00:00:00"
        mock_template.deleted_at = None
        
        mock_templates = [mock_template]
        mock_get_templates.return_value = mock_templates
        mock_count.return_value = 1
        
        response = test_client.get("/api/v1/templates?page=2&per_page=5&active_only=true&include_deleted=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["per_page"] == 5
        
        mock_get_templates.assert_called_once_with(
            mock_db, skip=5, limit=5, include_deleted=True, active_only=True
        )

    @patch('api.routers.templates.get_template_by_id')
    def test_get_template_success(self, mock_get_template, test_client, mock_db):
        """Test successful template retrieval."""
        mock_template = Mock()
        mock_template.id = 1
        mock_template.name = "Test Template"
        mock_template.description = "Test template"
        mock_template.template_content = "Hello {product_name}"
        mock_template.is_active = True
        mock_template.created_at = "2023-01-01T00:00:00"
        mock_template.updated_at = "2023-01-01T00:00:00"
        mock_template.deleted_at = None
        mock_get_template.return_value = mock_template
        
        response = test_client.get("/api/v1/templates/1")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["message"] == "Template retrieved successfully"
        
        mock_get_template.assert_called_once_with(mock_db, template_id=1)

    @patch('api.routers.templates.get_template_by_id')
    def test_get_template_not_found(self, mock_get_template, test_client):
        """Test template retrieval when template not found."""
        mock_get_template.return_value = None
        
        response = test_client.get("/api/v1/templates/999")
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]

    @patch('api.routers.templates.validate_template_content')
    @patch('api.routers.templates.create_template')
    def test_create_template_success(self, mock_create, mock_validate, test_client, mock_db):
        """Test successful template creation."""
        mock_validate.return_value = {"is_valid": True, "placeholders": []}
        mock_template = Mock()
        mock_template.id = 1
        mock_template.name = "New Template"
        mock_template.description = "A test template"
        mock_template.template_content = "Hello {product_name}"
        mock_template.is_active = True
        mock_template.created_at = "2023-01-01T00:00:00"
        mock_template.updated_at = "2023-01-01T00:00:00"
        mock_template.deleted_at = None
        mock_create.return_value = mock_template
        
        template_data = {
            "name": "New Template",
            "template_content": "Hello {product_name}",
            "description": "A test template",
            "is_active": True
        }
        
        response = test_client.post("/api/v1/templates", json=template_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Template created successfully"
        
        mock_validate.assert_called_once_with("Hello {product_name}")
        mock_create.assert_called_once()

    @patch('api.routers.templates.validate_template_content')
    def test_create_template_invalid_content(self, mock_validate, test_client):
        """Test template creation with invalid content."""
        mock_validate.return_value = {
            "is_valid": False, 
            "invalid_placeholders": ["{invalid_placeholder}"]
        }
        
        template_data = {
            "name": "Invalid Template",
            "template_content": "Hello {invalid_placeholder}",
            "description": "A test template",
            "is_active": True
        }
        
        response = test_client.post("/api/v1/templates", json=template_data)
        
        assert response.status_code == 400
        assert "invalid placeholders" in response.json()["detail"]

    @patch('api.routers.templates.get_template_by_id')
    @patch('api.routers.templates.validate_template_content')
    @patch('api.routers.templates.update_template')
    def test_update_template_success(self, mock_update, mock_validate, mock_get_template, test_client, mock_db):
        """Test successful template update."""
        mock_existing = Mock()
        mock_existing.id = 1
        mock_existing.name = "Existing Template"
        mock_get_template.return_value = mock_existing
        mock_validate.return_value = {"is_valid": True, "placeholders": []}
        
        mock_updated = Mock()
        mock_updated.id = 1
        mock_updated.name = "Updated Template"
        mock_updated.description = "Updated description"
        mock_updated.template_content = "Updated {product_name}"
        mock_updated.is_active = True
        mock_updated.created_at = "2023-01-01T00:00:00"
        mock_updated.updated_at = "2023-01-01T00:00:00"
        mock_updated.deleted_at = None
        mock_update.return_value = mock_updated
        
        update_data = {
            "name": "Updated Template",
            "template_content": "Updated {product_name}"
        }
        
        response = test_client.put("/api/v1/templates/1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Template updated successfully"
        
        mock_get_template.assert_called_once_with(mock_db, template_id=1)
        mock_validate.assert_called_once_with("Updated {product_name}")
        mock_update.assert_called_once()

    @patch('api.routers.templates.get_template_by_id')
    def test_update_template_not_found(self, mock_get_template, test_client):
        """Test template update when template not found."""
        mock_get_template.return_value = None
        
        update_data = {"name": "Updated Template"}
        
        response = test_client.put("/api/v1/templates/999", json=update_data)
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]

    @patch('api.routers.templates.get_template_by_id')
    @patch('api.routers.templates.soft_delete_template')
    def test_delete_template_success(self, mock_delete, mock_get_template, test_client, mock_db):
        """Test successful template deletion."""
        mock_template = Mock(id=1, name="Template to Delete")
        mock_get_template.return_value = mock_template
        mock_delete.return_value = True
        
        response = test_client.delete("/api/v1/templates/1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_id"] == 1
        assert data["message"] == "Template deleted successfully"
        
        mock_delete.assert_called_once_with(db=mock_db, template_id=1)

    @patch('api.routers.templates.get_template_by_id')
    def test_delete_template_not_found(self, mock_get_template, test_client):
        """Test template deletion when template not found."""
        mock_get_template.return_value = None
        
        response = test_client.delete("/api/v1/templates/999")
        
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]

    @patch('api.routers.templates.get_template_by_id')
    @patch('api.routers.templates.restore_template')
    def test_restore_template_success(self, mock_restore, mock_get_template, test_client, mock_db):
        """Test successful template restoration."""
        mock_deleted_template = Mock()
        mock_deleted_template.id = 1
        mock_deleted_template.name = "Deleted Template"
        mock_deleted_template.deleted_at = "2023-01-01"
        
        mock_restored_template = Mock()
        mock_restored_template.id = 1
        mock_restored_template.name = "Restored Template"
        mock_restored_template.description = "Restored template"
        mock_restored_template.template_content = "Hello {product_name}"
        mock_restored_template.is_active = True
        mock_restored_template.created_at = "2023-01-01T00:00:00"
        mock_restored_template.updated_at = "2023-01-01T00:00:00"
        mock_restored_template.deleted_at = None
        
        # Mock two calls to get_template_by_id: first with include_deleted, then after restore
        mock_get_template.side_effect = [mock_deleted_template, mock_restored_template]
        mock_restore.return_value = True
        
        response = test_client.post("/api/v1/templates/1/restore")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Template restored successfully"
        
        mock_restore.assert_called_once_with(db=mock_db, template_id=1)

    @patch('api.routers.templates.get_template_by_id')
    def test_restore_template_not_deleted(self, mock_get_template, test_client):
        """Test template restoration when template is not deleted."""
        mock_template = Mock(id=1, name="Active Template", deleted_at=None)
        mock_get_template.return_value = mock_template
        
        response = test_client.post("/api/v1/templates/1/restore")
        
        assert response.status_code == 400
        assert "not deleted and cannot be restored" in response.json()["detail"]

    @patch('api.routers.templates.preview_template_with_product')
    def test_preview_template_success(self, mock_preview, test_client, mock_db):
        """Test successful template preview."""
        mock_preview.return_value = {
            "rendered_content": "Hello Product A",
            "available_placeholders": ["{product_name}", "{product_price}"]
        }
        
        preview_data = {
            "template_content": "Hello {product_name}",
            "product_id": 1
        }
        
        response = test_client.post("/api/v1/templates/preview", json=preview_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["rendered_content"] == "Hello Product A"
        assert "{product_name}" in data["available_placeholders"]
        
        mock_preview.assert_called_once_with(
            db=mock_db,
            template_content="Hello {product_name}",
            product_id=1
        )

    @patch('api.routers.templates.preview_template_with_product')
    def test_preview_template_validation_error(self, mock_preview, test_client):
        """Test template preview with validation error."""
        mock_preview.side_effect = ValidationException("Invalid template content")
        
        preview_data = {
            "template_content": "Hello {invalid_placeholder}",
            "product_id": 1
        }
        
        response = test_client.post("/api/v1/templates/preview", json=preview_data)
        
        assert response.status_code == 400
        assert "Invalid template content" in response.json()["detail"]

    @patch('api.routers.templates.render_template_with_product')
    def test_render_template_success(self, mock_render, test_client, mock_db):
        """Test successful template rendering."""
        mock_render.return_value = {
            "template_name": "Welcome Template",
            "rendered_content": "Welcome to Product A",
            "product_name": "Product A",
            "product_url": "https://example.com/product-a"
        }
        
        render_data = {
            "template_id": 1,
            "product_id": 1
        }
        
        response = test_client.post("/api/v1/templates/render", json=render_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["template_name"] == "Welcome Template"
        assert data["rendered_content"] == "Welcome to Product A"
        assert data["product_name"] == "Product A"
        
        mock_render.assert_called_once_with(
            db=mock_db,
            template_id=1,
            product_id=1
        )

    @patch('api.routers.templates.get_template_placeholders')
    def test_get_available_placeholders(self, mock_get_placeholders, test_client):
        """Test getting available template placeholders."""
        mock_placeholders = {
            "product_name": "Name of the product",
            "product_price": "Price of the product",
            "product_url": "URL to the product page"
        }
        mock_get_placeholders.return_value = mock_placeholders
        
        response = test_client.get("/api/v1/templates/placeholders/available")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["count"] == 3
        assert "product_name" in data["data"]["placeholders"]
        assert data["message"] == "Retrieved 3 available placeholders"

    @patch('api.routers.templates.validate_template_content')
    def test_validate_template_content(self, mock_validate, test_client):
        """Test template content validation."""
        mock_validate.return_value = {
            "is_valid": True,
            "placeholders": ["{product_name}"],
            "invalid_placeholders": []
        }
        
        response = test_client.post("/api/v1/templates/validate?template_content=Hello {product_name}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_valid"] is True
        assert "{product_name}" in data["data"]["placeholders"]
        assert data["message"] == "Template validation completed"
        
        mock_validate.assert_called_once_with("Hello {product_name}")

    def test_calculate_pagination_helper(self, test_client):
        """Test calculate_pagination helper function."""
        from api.routers.templates import calculate_pagination
        
        # Test basic pagination
        pagination = calculate_pagination(page=1, per_page=10, total=25)
        assert pagination.page == 1
        assert pagination.per_page == 10
        assert pagination.total == 25
        assert pagination.pages == 3
        assert pagination.has_next is True
        assert pagination.has_prev is False
        
        # Test last page
        pagination = calculate_pagination(page=3, per_page=10, total=25)
        assert pagination.has_next is False
        assert pagination.has_prev is True
        
        # Test exact division
        pagination = calculate_pagination(page=2, per_page=10, total=20)
        assert pagination.pages == 2
        assert pagination.has_next is False


class TestTemplatesRouterErrorHandling:
    """Test error handling in templates router."""

    def test_invalid_template_id_parameter(self, test_client):
        """Test invalid template ID parameter."""
        response = test_client.get("/api/v1/templates/invalid")
        assert response.status_code == 422  # Validation error
        
        response = test_client.get("/api/v1/templates/0")
        assert response.status_code == 422  # ID must be >= 1

    def test_invalid_pagination_parameters(self, test_client):
        """Test invalid pagination parameters."""
        # Invalid page number
        response = test_client.get("/api/v1/templates?page=0")
        assert response.status_code == 422
        
        # Invalid per_page (too high)
        response = test_client.get("/api/v1/templates?per_page=200")
        assert response.status_code == 422

    def test_invalid_request_body(self, test_client):
        """Test invalid request body for POST endpoints."""
        # Missing required fields
        response = test_client.post("/api/v1/templates", json={})
        assert response.status_code == 422
        
        # Invalid field types
        response = test_client.post("/api/v1/templates", json={
            "name": 123,  # Should be string
            "template_content": "Hello {product_name}",
            "is_active": "invalid"  # Should be boolean
        })
        assert response.status_code == 422