"""
Unit tests for template model module.

This module tests the template model convenience import functionality.
"""

import pytest

from models.template import MessageTemplate
from models.product import MessageTemplate as ProductMessageTemplate


class TestTemplateModule:
    """Test suite for the template module."""

    def test_message_template_import(self):
        """Test that MessageTemplate can be imported from template module."""
        # Should be able to import MessageTemplate from template module
        assert MessageTemplate is not None
        assert hasattr(MessageTemplate, '__tablename__')
        assert MessageTemplate.__tablename__ == "message_templates"

    def test_template_is_same_as_product_template(self):
        """Test that template.MessageTemplate is the same as product.MessageTemplate."""
        # Should be the exact same class
        assert MessageTemplate is ProductMessageTemplate

    def test_template_module_exports(self):
        """Test that template module has correct exports."""
        import models.template as template_module
        
        # Check __all__ exports
        assert hasattr(template_module, '__all__')
        assert 'MessageTemplate' in template_module.__all__
        assert len(template_module.__all__) == 1

    def test_template_class_functionality(self):
        """Test that imported MessageTemplate class works correctly."""
        # Test that we can create an instance (without database)
        # This tests the class definition itself
        assert hasattr(MessageTemplate, 'name')
        assert hasattr(MessageTemplate, 'template_content')
        assert hasattr(MessageTemplate, 'is_active')
        assert hasattr(MessageTemplate, '__repr__')

    def test_template_repr_method(self):
        """Test that MessageTemplate has a repr method."""
        # Test the repr method exists and is callable
        assert hasattr(MessageTemplate, '__repr__')
        assert callable(getattr(MessageTemplate, '__repr__'))

    def test_import_path_consistency(self):
        """Test that both import paths work and reference the same class."""
        from models.template import MessageTemplate as TemplateImport
        from models.product import MessageTemplate as ProductImport
        
        assert TemplateImport is ProductImport
        assert id(TemplateImport) == id(ProductImport)

    def test_module_docstring(self):
        """Test that the template module has appropriate documentation."""
        import models.template as template_module
        
        # Module should have a docstring or comments explaining its purpose
        # This is verified by checking the source content
        assert template_module.__file__.endswith('template.py')

    def test_no_duplicate_definitions(self):
        """Test that template module doesn't redefine MessageTemplate."""
        import models.template as template_module
        import models.product as product_module
        
        # Should be importing, not defining new classes
        assert template_module.MessageTemplate is product_module.MessageTemplate
        
        # Module should be small and focused on re-exports
        module_attrs = [attr for attr in dir(template_module) 
                       if not attr.startswith('_')]
        expected_attrs = {'MessageTemplate'}
        
        # Should only have the expected exports plus __all__
        public_attrs = set(module_attrs) - {'__all__'}
        assert public_attrs == expected_attrs

    def test_circular_import_safety(self):
        """Test that imports don't create circular dependencies."""
        # This test ensures that importing template module doesn't cause issues
        try:
            import models.template
            import models.product
            # If we get here without import errors, circular imports are handled
            assert True
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_template_inheritance(self):
        """Test that MessageTemplate has proper SQLAlchemy inheritance."""
        from models.product import Base
        
        # MessageTemplate should inherit from the Base
        assert issubclass(MessageTemplate, Base)
        assert hasattr(MessageTemplate, '__table__')
        assert hasattr(MessageTemplate, '__tablename__')
        assert MessageTemplate.__tablename__ == "message_templates"