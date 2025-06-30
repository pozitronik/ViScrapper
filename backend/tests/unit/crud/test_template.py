"""
Comprehensive unit tests for template CRUD operations.

This module contains extensive tests for all template CRUD functions including
get_template_by_id, get_template_by_name, get_templates, create_template,
update_template, soft_delete_template, restore_template, and get_template_count.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from crud.template import (
    get_template_by_id,
    get_template_by_name,
    get_templates,
    create_template,
    update_template,
    soft_delete_template,
    restore_template,
    get_template_count
)
from models.template import MessageTemplate
from schemas.template import MessageTemplateCreate, MessageTemplateUpdate
from exceptions.base import DatabaseException, ValidationException


class TestGetTemplateById:
    """Test suite for get_template_by_id function."""

    def test_get_template_by_id_found(self):
        """Test successful template retrieval by ID."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.name = "Test Template"
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_template
        
        result = get_template_by_id(mock_db, 123)
        
        assert result == mock_template
        mock_db.query.assert_called_once_with(MessageTemplate)

    def test_get_template_by_id_not_found(self):
        """Test template retrieval when ID not found."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        result = get_template_by_id(mock_db, 999)
        
        assert result is None

    def test_get_template_by_id_include_deleted(self):
        """Test template retrieval with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        result = get_template_by_id(mock_db, 123, include_deleted=True)
        
        assert result == mock_template
        # Should not call filter twice when include_deleted=True
        query_mock = mock_db.query.return_value.filter.return_value
        query_mock.filter.assert_not_called()

    def test_get_template_by_id_database_exception(self):
        """Test template retrieval with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_template_by_id(mock_db, 123)
        
        assert "Failed to retrieve template by ID" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_template_by_id"
        assert exc_info.value.details["template_id"] == 123

    def test_get_template_by_id_logging(self):
        """Test logging behavior in get_template_by_id."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.name = "Test Template"
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_template
        
        with patch('crud.template.logger') as mock_logger:
            result = get_template_by_id(mock_db, 123)
            
            assert result == mock_template
            mock_logger.debug.assert_called()
            # Should log both search and found messages
            assert mock_logger.debug.call_count == 2


class TestGetTemplateByName:
    """Test suite for get_template_by_name function."""

    def test_get_template_by_name_found(self):
        """Test successful template retrieval by name."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.id = 123
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_template
        
        result = get_template_by_name(mock_db, "Test Template")
        
        assert result == mock_template
        mock_db.query.assert_called_once_with(MessageTemplate)

    def test_get_template_by_name_not_found(self):
        """Test template retrieval when name not found."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = None
        
        result = get_template_by_name(mock_db, "Nonexistent Template")
        
        assert result is None

    def test_get_template_by_name_include_deleted(self):
        """Test template retrieval by name with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        result = get_template_by_name(mock_db, "Test Template", include_deleted=True)
        
        assert result == mock_template

    def test_get_template_by_name_database_exception(self):
        """Test template retrieval by name with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_template_by_name(mock_db, "Test Template")
        
        assert "Failed to retrieve template by name" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_template_by_name"
        assert exc_info.value.details["name"] == "Test Template"

    def test_get_template_by_name_logging(self):
        """Test logging behavior in get_template_by_name."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.id = 123
        
        mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_template
        
        with patch('crud.template.logger') as mock_logger:
            result = get_template_by_name(mock_db, "Test Template")
            
            assert result == mock_template
            mock_logger.debug.assert_called()
            # Should log both search and found messages
            assert mock_logger.debug.call_count == 2


class TestGetTemplates:
    """Test suite for get_templates function."""

    def test_get_templates_success(self):
        """Test successful templates retrieval."""
        mock_db = Mock(spec=Session)
        mock_templates = [Mock(spec=MessageTemplate), Mock(spec=MessageTemplate)]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_templates
        
        result = get_templates(mock_db, skip=10, limit=20)
        
        assert result == mock_templates
        mock_db.query.assert_called_once_with(MessageTemplate)

    def test_get_templates_include_deleted(self):
        """Test templates retrieval with include_deleted flag."""
        mock_db = Mock(spec=Session)
        mock_templates = [Mock(spec=MessageTemplate)]
        
        mock_db.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_templates
        
        result = get_templates(mock_db, include_deleted=True)
        
        assert result == mock_templates

    def test_get_templates_active_only(self):
        """Test templates retrieval with active_only flag."""
        mock_db = Mock(spec=Session)
        mock_templates = [Mock(spec=MessageTemplate)]
        
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_templates
        
        result = get_templates(mock_db, active_only=True)
        
        assert result == mock_templates

    def test_get_templates_database_exception(self):
        """Test templates retrieval with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_templates(mock_db)
        
        assert "Failed to retrieve templates list" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_templates"

    def test_get_templates_logging(self):
        """Test logging behavior in get_templates."""
        mock_db = Mock(spec=Session)
        mock_templates = [Mock(spec=MessageTemplate)]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_templates
        
        with patch('crud.template.logger') as mock_logger:
            result = get_templates(mock_db, skip=5, limit=10)
            
            assert result == mock_templates
            mock_logger.debug.assert_called()
            # Should log both fetch and result messages
            assert mock_logger.debug.call_count == 2


class TestCreateTemplate:
    """Test suite for create_template function."""

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_name')
    def test_create_template_success(self, mock_get_by_name, mock_atomic):
        """Test successful template creation."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Test Template"
        mock_template_data.description = "A test template"
        mock_template_data.template_content = "Hello {{name}}"
        mock_template_data.is_active = True
        
        # Mock no existing template
        mock_get_by_name.return_value = None
        
        # Mock database operations
        mock_db.add.return_value = None
        mock_db.flush.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = create_template(mock_db, mock_template_data)
        
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_get_by_name.assert_called_once_with(mock_db, "Test Template")

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_name')
    def test_create_template_duplicate_name(self, mock_get_by_name, mock_atomic):
        """Test template creation with duplicate name."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Existing Template"
        
        # Mock existing template
        mock_existing_template = Mock(spec=MessageTemplate)
        mock_existing_template.id = 123
        mock_get_by_name.return_value = mock_existing_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            create_template(mock_db, mock_template_data)
        
        assert "Template with this name already exists" in str(exc_info.value)
        assert exc_info.value.details["name"] == "Existing Template"
        assert exc_info.value.details["existing_id"] == 123

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_name')
    def test_create_template_integrity_error(self, mock_get_by_name, mock_atomic):
        """Test template creation with integrity error."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Test Template"
        
        # Mock no existing template
        mock_get_by_name.return_value = None
        
        # Mock integrity error
        integrity_error = IntegrityError("statement", "params", "orig")
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="UNIQUE constraint failed: message_templates.name")
        
        mock_atomic.return_value.__enter__.side_effect = integrity_error
        
        with pytest.raises(ValidationException) as exc_info:
            create_template(mock_db, mock_template_data)
        
        assert "Template name already exists" in str(exc_info.value)
        assert exc_info.value.details["name"] == "Test Template"

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_name')
    def test_create_template_other_integrity_error(self, mock_get_by_name, mock_atomic):
        """Test template creation with other integrity error."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Test Template"
        
        # Mock no existing template
        mock_get_by_name.return_value = None
        
        # Mock other integrity error
        integrity_error = IntegrityError("statement", "params", "orig")
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="FOREIGN KEY constraint failed")
        
        mock_atomic.return_value.__enter__.side_effect = integrity_error
        
        with pytest.raises(DatabaseException) as exc_info:
            create_template(mock_db, mock_template_data)
        
        assert "Database constraint violation during template creation" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "create_template"

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_name')
    def test_create_template_database_exception(self, mock_get_by_name, mock_atomic):
        """Test template creation with database exception."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Test Template"
        
        # Mock no existing template
        mock_get_by_name.return_value = None
        
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            create_template(mock_db, mock_template_data)
        
        assert "Failed to create template" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "create_template"

    def test_create_template_logging(self):
        """Test logging behavior in create_template."""
        mock_db = Mock(spec=Session)
        mock_template_data = Mock(spec=MessageTemplateCreate)
        mock_template_data.name = "Test Template"
        
        with patch('crud.template.logger') as mock_logger:
            with patch('crud.template.get_template_by_name', return_value=None):
                with patch('crud.template.atomic_transaction') as mock_atomic:
                    mock_atomic.return_value.__enter__.side_effect = Exception("Test error")
                    
                    with pytest.raises(DatabaseException):
                        create_template(mock_db, mock_template_data)
                    
                    mock_logger.info.assert_called()
                    assert "Creating template" in str(mock_logger.info.call_args)


class TestUpdateTemplate:
    """Test suite for update_template function."""

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    @patch('crud.template.get_template_by_name')
    def test_update_template_success(self, mock_get_by_name, mock_get_by_id, mock_atomic):
        """Test successful template update."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.name = "Old Template"
        
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        mock_template_update.model_dump.return_value = {"name": "Updated Template", "is_active": False}
        
        mock_get_by_id.return_value = mock_template
        mock_get_by_name.return_value = None  # No existing template with the new name
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = update_template(mock_db, 123, mock_template_update)
        
        assert result == mock_template
        mock_db.flush.assert_called_once()
        assert mock_template.updated_at is not None

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    def test_update_template_not_found(self, mock_get_by_id, mock_atomic):
        """Test template update when template not found."""
        mock_db = Mock(spec=Session)
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        
        mock_get_by_id.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            update_template(mock_db, 999, mock_template_update)
        
        assert "Template not found for update" in str(exc_info.value)
        assert exc_info.value.details["template_id"] == 999

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    @patch('crud.template.get_template_by_name')
    def test_update_template_duplicate_name(self, mock_get_by_name, mock_get_by_id, mock_atomic):
        """Test template update with duplicate name."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.name = "Old Template"
        
        mock_existing_template = Mock(spec=MessageTemplate)
        mock_existing_template.id = 456
        
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        mock_template_update.model_dump.return_value = {"name": "Existing Template"}
        
        mock_get_by_id.return_value = mock_template
        mock_get_by_name.return_value = mock_existing_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            update_template(mock_db, 123, mock_template_update)
        
        assert "Template name already exists" in str(exc_info.value)
        assert exc_info.value.details["name"] == "Existing Template"
        assert exc_info.value.details["existing_id"] == 456

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    def test_update_template_no_changes(self, mock_get_by_id, mock_atomic):
        """Test template update with no changes."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        mock_template_update.model_dump.return_value = {}
        
        mock_get_by_id.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = update_template(mock_db, 123, mock_template_update)
        
        assert result == mock_template
        # flush should not be called when no changes
        mock_db.flush.assert_not_called()

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    def test_update_template_integrity_error(self, mock_get_by_id, mock_atomic):
        """Test template update with integrity error."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        mock_template_update.model_dump.return_value = {"name": "Updated"}
        
        mock_get_by_id.return_value = mock_template
        
        # Mock integrity error
        integrity_error = IntegrityError("statement", "params", "orig")
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = Mock(return_value="UNIQUE constraint failed: message_templates.name")
        
        mock_atomic.return_value.__enter__.side_effect = integrity_error
        
        with pytest.raises(ValidationException) as exc_info:
            update_template(mock_db, 123, mock_template_update)
        
        assert "Template name already exists" in str(exc_info.value)
        assert exc_info.value.details["template_id"] == 123

    @patch('crud.template.atomic_transaction')
    @patch('crud.template.get_template_by_id')
    def test_update_template_database_exception(self, mock_get_by_id, mock_atomic):
        """Test template update with database exception."""
        mock_db = Mock(spec=Session)
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        
        mock_get_by_id.return_value = Mock(spec=MessageTemplate)
        
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            update_template(mock_db, 123, mock_template_update)
        
        assert "Failed to update template" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "update_template"
        assert exc_info.value.details["template_id"] == 123

    def test_update_template_logging(self):
        """Test logging behavior in update_template."""
        mock_db = Mock(spec=Session)
        mock_template_update = Mock(spec=MessageTemplateUpdate)
        
        with patch('crud.template.logger') as mock_logger:
            with patch('crud.template.get_template_by_id', return_value=Mock(spec=MessageTemplate)):
                with patch('crud.template.atomic_transaction') as mock_atomic:
                    mock_atomic.return_value.__enter__.side_effect = Exception("Test error")
                    
                    with pytest.raises(DatabaseException):
                        update_template(mock_db, 123, mock_template_update)
                    
                    mock_logger.info.assert_called()
                    assert "Updating template with ID" in str(mock_logger.info.call_args)


class TestSoftDeleteTemplate:
    """Test suite for soft_delete_template function."""

    @patch('crud.template.atomic_transaction')
    def test_soft_delete_template_success(self, mock_atomic):
        """Test successful template soft deletion."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.deleted_at = None
        mock_template.is_active = True
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = soft_delete_template(mock_db, 123)
        
        assert result is True
        assert mock_template.deleted_at is not None
        assert mock_template.is_active is False
        mock_db.flush.assert_called_once()

    @patch('crud.template.atomic_transaction')
    def test_soft_delete_template_not_found(self, mock_atomic):
        """Test soft deletion when template not found."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            soft_delete_template(mock_db, 999)
        
        assert "Template not found for soft deletion" in str(exc_info.value)
        assert exc_info.value.details["template_id"] == 999

    @patch('crud.template.atomic_transaction')
    def test_soft_delete_template_already_deleted(self, mock_atomic):
        """Test soft deletion when template already soft deleted."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.deleted_at = datetime.now(timezone.utc)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.template.logger') as mock_logger:
            result = soft_delete_template(mock_db, 123)
            
            assert result is True
            mock_logger.warning.assert_called()
            assert "already soft deleted" in str(mock_logger.warning.call_args)

    @patch('crud.template.atomic_transaction')
    def test_soft_delete_template_database_exception(self, mock_atomic):
        """Test soft deletion with database exception."""
        mock_db = Mock(spec=Session)
        
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            soft_delete_template(mock_db, 123)
        
        assert "Failed to soft delete template" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "soft_delete_template"
        assert exc_info.value.details["template_id"] == 123

    @patch('crud.template.atomic_transaction')
    def test_soft_delete_template_logging(self, mock_atomic):
        """Test logging behavior in soft_delete_template."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.deleted_at = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.template.logger') as mock_logger:
            result = soft_delete_template(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log both start and success messages
            assert mock_logger.info.call_count == 2


class TestRestoreTemplate:
    """Test suite for restore_template function."""

    @patch('crud.template.atomic_transaction')
    def test_restore_template_success(self, mock_atomic):
        """Test successful template restoration."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.deleted_at = datetime.now(timezone.utc)
        mock_template.is_active = False
        
        # Mock query chain for soft-deleted template
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        result = restore_template(mock_db, 123)
        
        assert result is True
        assert mock_template.deleted_at is None
        assert mock_template.is_active is True
        mock_db.flush.assert_called_once()

    @patch('crud.template.atomic_transaction')
    def test_restore_template_not_found(self, mock_atomic):
        """Test restoration when template not found."""
        mock_db = Mock(spec=Session)
        
        # Mock both queries return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            restore_template(mock_db, 999)
        
        assert "Template not found for restoration" in str(exc_info.value)
        assert exc_info.value.details["template_id"] == 999

    @patch('crud.template.atomic_transaction')
    def test_restore_template_not_soft_deleted(self, mock_atomic):
        """Test restoration when template is not soft deleted."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        
        # Create separate mock queries
        mock_soft_deleted_query = Mock()
        mock_soft_deleted_query.filter.return_value.first.return_value = None
        
        mock_regular_query = Mock()
        mock_regular_query.filter.return_value.first.return_value = mock_template
        
        # Configure query calls to return different mocks
        call_count = 0
        def query_side_effect(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First call - soft deleted query
                return mock_soft_deleted_query
            else:  # Second call - regular query
                return mock_regular_query
        
        mock_db.query.side_effect = query_side_effect
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with pytest.raises(ValidationException) as exc_info:
            restore_template(mock_db, 123)
        
        assert "Template is not soft deleted and cannot be restored" in str(exc_info.value)
        assert exc_info.value.details["template_id"] == 123

    @patch('crud.template.atomic_transaction')
    def test_restore_template_database_exception(self, mock_atomic):
        """Test restoration with database exception."""
        mock_db = Mock(spec=Session)
        
        mock_atomic.return_value.__enter__.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            restore_template(mock_db, 123)
        
        assert "Failed to restore template" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "restore_template"
        assert exc_info.value.details["template_id"] == 123

    @patch('crud.template.atomic_transaction')
    def test_restore_template_logging(self, mock_atomic):
        """Test logging behavior in restore_template."""
        mock_db = Mock(spec=Session)
        mock_template = Mock(spec=MessageTemplate)
        mock_template.deleted_at = datetime.now(timezone.utc)
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_template
        
        # Mock atomic transaction
        mock_atomic.return_value.__enter__ = Mock()
        mock_atomic.return_value.__exit__ = Mock(return_value=None)
        
        with patch('crud.template.logger') as mock_logger:
            result = restore_template(mock_db, 123)
            
            assert result is True
            mock_logger.info.assert_called()
            # Should log both start and success messages
            assert mock_logger.info.call_count == 2


class TestGetTemplateCount:
    """Test suite for get_template_count function."""

    def test_get_template_count_success(self):
        """Test successful template count retrieval."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        result = get_template_count(mock_db)
        
        assert result == 5
        mock_db.query.assert_called_once_with(MessageTemplate)

    def test_get_template_count_include_deleted(self):
        """Test template count with include_deleted flag."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.count.return_value = 10
        
        result = get_template_count(mock_db, include_deleted=True)
        
        assert result == 10

    def test_get_template_count_active_only(self):
        """Test template count with active_only flag."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.filter.return_value.count.return_value = 3
        
        result = get_template_count(mock_db, active_only=True)
        
        assert result == 3

    def test_get_template_count_both_flags(self):
        """Test template count with both include_deleted and active_only flags."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.count.return_value = 2
        
        result = get_template_count(mock_db, include_deleted=True, active_only=True)
        
        assert result == 2

    def test_get_template_count_database_exception(self):
        """Test template count with database exception."""
        mock_db = Mock(spec=Session)
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseException) as exc_info:
            get_template_count(mock_db)
        
        assert "Failed to get template count" in str(exc_info.value)
        assert exc_info.value.details["operation"] == "get_template_count"

    def test_get_template_count_logging(self):
        """Test logging behavior in get_template_count."""
        mock_db = Mock(spec=Session)
        
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        with patch('crud.template.logger') as mock_logger:
            result = get_template_count(mock_db)
            
            assert result == 5
            mock_logger.debug.assert_called()
            assert "Total template count: 5" in str(mock_logger.debug.call_args)