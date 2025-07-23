"""
Tests for template_service.py
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from services.template_service import (
    TemplateRenderer, 
    template_renderer,
    render_template_with_product,
    preview_template_with_product,
    get_template_placeholders,
    validate_template_content
)
from exceptions.base import ValidationException
from models.product import Product, Size, Image, MessageTemplate


class TestTemplateRenderer:
    """Test TemplateRenderer class"""
    
    def test_init(self):
        """Test renderer initialization"""
        renderer = TemplateRenderer()
        assert renderer.placeholder_pattern is not None
        assert hasattr(renderer, 'AVAILABLE_PLACEHOLDERS')
    
    def test_get_available_placeholders(self):
        """Test getting list of available placeholders"""
        renderer = TemplateRenderer()
        placeholders = renderer.get_available_placeholders()
        
        assert isinstance(placeholders, list)
        assert len(placeholders) > 0
        assert '{name}' in placeholders
        assert '{product_name}' in placeholders
        assert '{current_date}' in placeholders
    
    def test_get_placeholder_descriptions(self):
        """Test getting placeholder descriptions"""
        renderer = TemplateRenderer()
        descriptions = renderer.get_placeholder_descriptions()
        
        assert isinstance(descriptions, dict)
        assert '{name}' in descriptions
        assert descriptions['{name}'] == 'Product name'
        assert '{current_date}' in descriptions
    
    def test_extract_placeholders_simple(self):
        """Test extracting placeholders from template content"""
        renderer = TemplateRenderer()
        template = "Hello {name}, price is {price}"
        
        placeholders = renderer.extract_placeholders(template)
        
        assert placeholders == ['{name}', '{price}']
    
    def test_extract_placeholders_complex(self):
        """Test extracting placeholders with complex content"""
        renderer = TemplateRenderer()
        template = "Product: {name}\nSKU: {sku}\nSizes: {sizes}\nPrice: {price} {currency}"
        
        placeholders = renderer.extract_placeholders(template)
        
        expected = ['{name}', '{sku}', '{sizes}', '{price}', '{currency}']
        assert placeholders == expected
    
    def test_extract_placeholders_no_placeholders(self):
        """Test extracting placeholders when none exist"""
        renderer = TemplateRenderer()
        template = "This template has no placeholders"
        
        placeholders = renderer.extract_placeholders(template)
        
        assert placeholders == []
    
    def test_extract_placeholders_duplicate(self):
        """Test extracting placeholders with duplicates"""
        renderer = TemplateRenderer()
        template = "Name: {name}, again name: {name}"
        
        placeholders = renderer.extract_placeholders(template)
        
        assert placeholders == ['{name}', '{name}']
    
    def test_validate_placeholders_valid(self):
        """Test validating valid placeholders"""
        renderer = TemplateRenderer()
        template = "Product {name} costs {price} {currency}"
        
        invalid = renderer.validate_placeholders(template)
        
        assert invalid == []
    
    def test_validate_placeholders_invalid(self):
        """Test validating invalid placeholders"""
        renderer = TemplateRenderer()
        template = "Product {name} has {invalid_placeholder} and {another_invalid}"
        
        invalid = renderer.validate_placeholders(template)
        
        assert '{invalid_placeholder}' in invalid
        assert '{another_invalid}' in invalid
        assert len(invalid) == 2
    
    def test_validate_placeholders_mixed(self):
        """Test validating mix of valid and invalid placeholders"""
        renderer = TemplateRenderer()
        template = "Product {name} costs {price} and has {invalid_field}"
        
        invalid = renderer.validate_placeholders(template)
        
        assert invalid == ['{invalid_field}']
    
    def test_format_sizes_for_display_no_sizes(self):
        """Test formatting sizes when product has no sizes"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.sizes = []
        
        display, all_sizes, multiline = renderer._format_sizes_for_display(product)
        
        assert display == 'None'
        assert all_sizes == []
        assert multiline == 'None'
    
    def test_format_sizes_for_display_simple_sizes(self):
        """Test formatting simple sizes"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        
        size1 = Mock(spec=Size)
        size1.size_type = 'simple'
        size1.size_value = 'M'
        size1.deleted_at = None
        
        size2 = Mock(spec=Size)
        size2.size_type = 'simple'
        size2.size_value = 'L'
        size2.deleted_at = None
        
        product.sizes = [size1, size2]
        
        display, all_sizes, multiline = renderer._format_sizes_for_display(product)
        
        assert display == 'M, L'
        assert set(all_sizes) == {'M', 'L'}
        assert multiline == 'M, L'  # Simple sizes use comma-separated format
    
    def test_format_sizes_for_display_combination_sizes(self):
        """Test formatting combination sizes"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        
        size = Mock(spec=Size)
        size.size_type = 'combination'
        size.combination_data = {
            '32': ['A', 'B'],
            '34': ['A', 'C']
        }
        size.deleted_at = None
        
        product.sizes = [size]
        
        display, all_sizes, multiline = renderer._format_sizes_for_display(product)
        
        assert '32: A B' in display
        assert '34: A C' in display
        assert set(all_sizes) == {'32A', '32B', '34A', '34C'}
        # Multiline format for combinations
        assert '32: A, B' in multiline
        assert '34: A, C' in multiline
    
    def test_format_sizes_for_display_deleted_sizes_excluded(self):
        """Test that deleted sizes are excluded"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        
        size1 = Mock(spec=Size)
        size1.size_type = 'simple'
        size1.size_value = 'M'
        size1.deleted_at = None
        
        size2 = Mock(spec=Size)
        size2.size_type = 'simple'
        size2.size_value = 'L'
        size2.deleted_at = datetime.now()  # Deleted
        
        product.sizes = [size1, size2]
        
        display, all_sizes, multiline = renderer._format_sizes_for_display(product)
        
        assert display == 'M'
        assert all_sizes == ['M']
        assert multiline == 'M'
    
    def test_get_product_data_basic(self):
        """Test getting basic product data"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test Product'
        product.sku = 'TEST123'
        product.price = 29.99
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = 'Cotton'
        product.item = 'Shirt'
        product.store = 'Test Store'
        product.comment = 'Great product'
        product.product_url = 'https://example.com/product'
        product.created_at = datetime(2024, 1, 15, 10, 30, 45)
        product.images = []
        product.sizes = []
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')):
            data = renderer._get_product_data(product)
        
        assert data['name'] == 'Test Product'
        assert data['sku'] == 'TEST123'
        assert data['price'] == '29.99'
        assert data['currency'] == 'USD'
        assert data['id'] == '123'
        assert data['created_at'] == '2024-01-15 10:30:45'
        
        # Test backwards compatibility (long format)
        assert data['product_name'] == 'Test Product'
        assert data['product_sku'] == 'TEST123'
    
    def test_get_product_data_with_images(self):
        """Test getting product data with images"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test Product'
        product.sku = 'TEST123'
        product.price = 29.99
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = 'Cotton'
        product.item = 'Shirt'
        product.store = 'Test Store'
        product.comment = 'Great product'
        product.product_url = 'https://example.com/product'
        product.created_at = datetime(2024, 1, 15, 10, 30, 45)
        
        image1 = Mock(spec=Image)
        image1.url = 'image1.jpg'
        image1.deleted_at = None
        
        image2 = Mock(spec=Image)
        image2.url = 'image2.jpg'
        image2.deleted_at = None
        
        product.images = [image1, image2]
        product.sizes = []
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')):
            data = renderer._get_product_data(product)
        
        assert data['images'] == 'image1.jpg, image2.jpg'
        assert data['images_count'] == '2'
    
    def test_get_product_data_none_values(self):
        """Test getting product data with None values"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = None
        product.sku = None
        product.price = None
        product.currency = None
        product.availability = None
        product.color = None
        product.composition = None
        product.item = None
        product.store = None
        product.comment = None
        product.product_url = None
        product.created_at = None
        product.images = None
        product.sizes = []
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')):
            data = renderer._get_product_data(product)
        
        assert data['name'] == 'Unnamed Product'
        assert data['sku'] == 'No SKU'
        assert data['price'] == '0.00'
        assert data['currency'] == 'USD'
        assert data['created_at'] == 'Unknown'
    
    @patch('services.template_service.ProductSchema')
    def test_get_product_data_sell_price_success(self, mock_product_schema):
        """Test getting product data with successful sell price calculation"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test Product'
        product.sku = 'TEST123'
        product.price = 29.99
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = 'Cotton'
        product.item = 'Shirt'
        product.store = 'Test Store'
        product.comment = 'Great product'
        product.product_url = 'https://example.com/product'
        product.created_at = datetime(2024, 1, 15, 10, 30, 45)
        product.images = []
        product.sizes = []
        
        # Mock ProductSchema
        mock_schema_instance = Mock()
        mock_schema_instance.sell_price = 35.50
        mock_product_schema.model_validate.return_value = mock_schema_instance
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')):
            data = renderer._get_product_data(product)
        
        assert data['sell_price'] == '35.5'
        assert data['product_sell_price'] == '35.5'
    
    @patch('services.template_service.ProductSchema')
    def test_get_product_data_sell_price_failure(self, mock_product_schema):
        """Test getting product data with failed sell price calculation"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test Product'
        product.sku = 'TEST123'
        product.price = 29.99
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = 'Cotton'
        product.item = 'Shirt'
        product.store = 'Test Store'
        product.comment = 'Great product'
        product.product_url = 'https://example.com/product'
        product.created_at = datetime(2024, 1, 15, 10, 30, 45)
        product.images = []
        product.sizes = []
        
        # Mock ProductSchema to raise exception
        mock_product_schema.model_validate.side_effect = Exception("Schema error")
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')):
            data = renderer._get_product_data(product)
        
        assert data['sell_price'] == '0'
        assert data['product_sell_price'] == '0'
    
    def test_get_current_data(self):
        """Test getting current date/time data"""
        renderer = TemplateRenderer()
        
        with patch('services.template_service.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 15, 14, 30, 45)
            mock_datetime.now.return_value = mock_now
            
            data = renderer._get_current_data()
        
        assert data['current_date'] == '2024-01-15'
        assert data['current_time'] == '14:30:45'
        assert data['current_datetime'] == '2024-01-15 14:30:45'
    
    def test_render_template_success(self):
        """Test successful template rendering"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        template = "Product: {name}, Price: {price} {currency}"
        
        with patch.object(renderer, 'validate_placeholders', return_value=[]), \
             patch.object(renderer, '_get_product_data', return_value={
                 'name': 'Test Product',
                 'price': '29.99',
                 'currency': 'USD'
             }), \
             patch.object(renderer, '_get_current_data', return_value={}):
            
            result = renderer.render_template(template, product)
        
        assert result == "Product: Test Product, Price: 29.99 USD"
    
    def test_render_template_invalid_placeholders(self):
        """Test template rendering with invalid placeholders"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        template = "Product: {name}, Invalid: {invalid_field}"
        
        # Don't mock validation - let it run naturally to trigger the exception
        with pytest.raises(ValidationException) as exc_info:
            renderer.render_template(template, product)
        
        exception_message = str(exc_info.value.message)
        assert "invalid placeholders" in exception_message
        assert "invalid_field" in str(exc_info.value.details)
    
    def test_render_template_with_current_data(self):
        """Test template rendering with current date/time placeholders"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        template = "Date: {current_date}, Product: {name}"
        
        with patch.object(renderer, 'validate_placeholders', return_value=[]), \
             patch.object(renderer, '_get_product_data', return_value={'name': 'Test Product'}), \
             patch.object(renderer, '_get_current_data', return_value={'current_date': '2024-01-15'}):
            
            result = renderer.render_template(template, product)
        
        assert result == "Date: 2024-01-15, Product: Test Product"
    
    def test_preview_template_success(self):
        """Test successful template preview"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.name = 'Test Product'
        product.id = 123
        template = "Product: {name}"
        
        with patch.object(renderer, 'render_template', return_value="Product: Test Product"), \
             patch.object(renderer, 'get_available_placeholders', return_value=['{name}']), \
             patch.object(renderer, 'extract_placeholders', return_value=['{name}']):
            
            result = renderer.preview_template(template, product)
        
        assert result['rendered_content'] == "Product: Test Product"
        assert result['product_name'] == 'Test Product'
        assert result['product_id'] == 123
        assert result['available_placeholders'] == ['{name}']
        assert result['used_placeholders'] == ['{name}']
    
    def test_preview_template_error(self):
        """Test template preview with error"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        template = "Product: {invalid}"
        
        with patch.object(renderer, 'render_template', side_effect=ValidationException("Invalid template")):
            with pytest.raises(ValidationException):
                renderer.preview_template(template, product)


class TestGlobalFunctions:
    """Test global template service functions"""
    
    def test_global_template_renderer(self):
        """Test global template renderer instance"""
        assert template_renderer is not None
        assert isinstance(template_renderer, TemplateRenderer)
    
    @patch('services.template_service.get_template_by_id')
    @patch('services.template_service.get_product_by_id')
    def test_render_template_with_product_success(self, mock_get_product, mock_get_template):
        """Test successful template rendering with product"""
        db = Mock(spec=Session)
        
        # Mock template
        template = Mock(spec=MessageTemplate)
        template.id = 1
        template.name = 'Test Template'
        template.template_content = 'Product: {name}'
        template.is_active = True
        mock_get_template.return_value = template
        
        # Mock product
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test Product'
        product.product_url = 'https://example.com/product'
        mock_get_product.return_value = product
        
        with patch.object(template_renderer, 'render_template', return_value='Product: Test Product'):
            result = render_template_with_product(db, 1, 123)
        
        assert result['template_id'] == 1
        assert result['template_name'] == 'Test Template'
        assert result['rendered_content'] == 'Product: Test Product'
        assert result['product_id'] == 123
        assert result['product_name'] == 'Test Product'
    
    @patch('services.template_service.get_template_by_id')
    def test_render_template_with_product_template_not_found(self, mock_get_template):
        """Test template rendering when template not found"""
        db = Mock(spec=Session)
        mock_get_template.return_value = None
        
        with pytest.raises(ValidationException) as exc_info:
            render_template_with_product(db, 999, 123)
        
        assert "Template not found" in str(exc_info.value)
    
    @patch('services.template_service.get_template_by_id')
    def test_render_template_with_product_template_inactive(self, mock_get_template):
        """Test template rendering when template is inactive"""
        db = Mock(spec=Session)
        
        template = Mock(spec=MessageTemplate)
        template.id = 1
        template.is_active = False
        mock_get_template.return_value = template
        
        with pytest.raises(ValidationException) as exc_info:
            render_template_with_product(db, 1, 123)
        
        assert "Template is not active" in str(exc_info.value)
    
    @patch('services.template_service.get_template_by_id')
    @patch('services.template_service.get_product_by_id')
    def test_render_template_with_product_product_not_found(self, mock_get_product, mock_get_template):
        """Test template rendering when product not found"""
        db = Mock(spec=Session)
        
        template = Mock(spec=MessageTemplate)
        template.is_active = True
        mock_get_template.return_value = template
        mock_get_product.return_value = None
        
        with pytest.raises(ValidationException) as exc_info:
            render_template_with_product(db, 1, 999)
        
        assert "Product not found" in str(exc_info.value)
    
    @patch('services.template_service.get_product_by_id')
    def test_preview_template_with_product_success(self, mock_get_product):
        """Test successful template preview with product"""
        db = Mock(spec=Session)
        
        product = Mock(spec=Product)
        product.id = 123
        mock_get_product.return_value = product
        
        template_content = 'Product: {name}'
        
        with patch.object(template_renderer, 'preview_template', return_value={'rendered_content': 'Product: Test'}):
            result = preview_template_with_product(db, template_content, 123)
        
        assert result['rendered_content'] == 'Product: Test'
    
    @patch('services.template_service.get_product_by_id')
    def test_preview_template_with_product_product_not_found(self, mock_get_product):
        """Test template preview when product not found"""
        db = Mock(spec=Session)
        mock_get_product.return_value = None
        
        with pytest.raises(ValidationException) as exc_info:
            preview_template_with_product(db, 'Template: {name}', 999)
        
        assert "Product not found" in str(exc_info.value)
    
    def test_get_template_placeholders(self):
        """Test getting template placeholders"""
        placeholders = get_template_placeholders()
        
        assert isinstance(placeholders, dict)
        assert '{name}' in placeholders
        assert '{current_date}' in placeholders
        assert placeholders['{name}'] == 'Product name'
    
    def test_validate_template_content_valid(self):
        """Test validating valid template content"""
        template_content = 'Product: {name}, Price: {price}'
        
        with patch.object(template_renderer, 'validate_placeholders', return_value=[]), \
             patch.object(template_renderer, 'extract_placeholders', return_value=['{name}', '{price}']), \
             patch.object(template_renderer, 'get_available_placeholders', return_value=['{name}', '{price}']):
            
            result = validate_template_content(template_content)
        
        assert result['is_valid'] is True
        assert result['invalid_placeholders'] == []
        assert result['used_placeholders'] == ['{name}', '{price}']
    
    def test_validate_template_content_invalid(self):
        """Test validating invalid template content"""
        template_content = 'Product: {name}, Invalid: {bad_field}'
        
        with patch.object(template_renderer, 'validate_placeholders', return_value=['{bad_field}']), \
             patch.object(template_renderer, 'extract_placeholders', return_value=['{name}', '{bad_field}']), \
             patch.object(template_renderer, 'get_available_placeholders', return_value=['{name}']):
            
            result = validate_template_content(template_content)
        
        assert result['is_valid'] is False
        assert result['invalid_placeholders'] == ['{bad_field}']
        assert result['used_placeholders'] == ['{name}', '{bad_field}']


class TestTemplateRendererIntegration:
    """Integration tests for template renderer"""
    
    def test_full_template_rendering_workflow(self):
        """Test complete template rendering workflow"""
        renderer = TemplateRenderer()
        
        # Create mock product with all fields
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Blue Cotton Shirt'
        product.sku = 'SHIRT-001'
        product.price = 29.99
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = '100% Cotton'
        product.item = 'Shirt'
        product.store = 'Fashion Store'
        product.comment = 'Great quality'
        product.product_url = 'https://example.com/shirt'
        product.created_at = datetime(2024, 1, 15, 10, 30, 45)
        
        # Mock images
        image1 = Mock(spec=Image)
        image1.url = 'shirt1.jpg'
        image1.deleted_at = None
        
        image2 = Mock(spec=Image)
        image2.url = 'shirt2.jpg'
        image2.deleted_at = None
        
        product.images = [image1, image2]
        
        # Mock sizes
        size = Mock(spec=Size)
        size.size_type = 'simple'
        size.size_value = 'M'
        size.deleted_at = None
        
        product.sizes = [size]
        
        template = """
Product: {name}
SKU: {sku}
Price: {price} {currency}
Availability: {availability}
Store: {store}
Images: {images_count}
Sizes: {sizes}
URL: {url}
Created: {created_at}
        """.strip()
        
        # Mock ProductSchema for sell_price
        with patch('services.template_service.ProductSchema') as mock_schema:
            mock_instance = Mock()
            mock_instance.sell_price = 35.50
            mock_schema.model_validate.return_value = mock_instance
            
            result = renderer.render_template(template, product)
        
        expected = """
Product: Blue Cotton Shirt
SKU: SHIRT-001
Price: 29.99 USD
Availability: In Stock
Store: Fashion Store
Images: 2
Sizes: M
URL: https://example.com/shirt
Created: 2024-01-15 10:30:45
        """.strip()
        
        assert result == expected


class TestTemplateRendererEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_render_template_empty_content(self):
        """Test rendering empty template content"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        
        with patch.object(renderer, '_get_product_data', return_value={}), \
             patch.object(renderer, '_get_current_data', return_value={}):
            result = renderer.render_template("", product)
        
        assert result == ""
    
    def test_render_template_no_placeholders(self):
        """Test rendering template with no placeholders"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        template = "This is a static template with no placeholders"
        
        with patch.object(renderer, '_get_product_data', return_value={}), \
             patch.object(renderer, '_get_current_data', return_value={}):
            result = renderer.render_template(template, product)
        
        assert result == template
    
    def test_extract_placeholders_malformed(self):
        """Test extracting placeholders from malformed template"""
        renderer = TemplateRenderer()
        template = "Product {name with no closing brace and {partial}"
        
        placeholders = renderer.extract_placeholders(template)
        
        # The regex extracts everything between braces, including malformed ones
        # This tests the actual behavior of the regex pattern
        assert len(placeholders) == 1
        assert "partial" in placeholders[0]
    
    def test_format_price_edge_cases(self):
        """Test price formatting edge cases"""
        renderer = TemplateRenderer()
        product = Mock(spec=Product)
        product.id = 123
        product.name = 'Test'
        product.sku = 'TEST'
        product.price = 0.0  # Zero price
        product.currency = 'USD'
        product.availability = 'In Stock'
        product.color = 'Blue'
        product.composition = 'Cotton'
        product.item = 'Shirt'
        product.store = 'Store'
        product.comment = 'Comment'
        product.product_url = 'http://example.com'
        product.created_at = datetime.now()
        product.images = []
        product.sizes = []
        
        with patch.object(renderer, '_format_sizes_for_display', return_value=('None', [], 'None')), \
             patch('services.template_service.ProductSchema') as mock_schema:
            
            mock_instance = Mock()
            mock_instance.sell_price = 0.0
            mock_schema.model_validate.return_value = mock_instance
            
            data = renderer._get_product_data(product)
        
        assert data['price'] == '0.0'
        assert data['sell_price'] == '0'
    
    def test_sizes_formatting_with_newline_for_combinations(self):
        """Test that combination sizes get a leading newline in the {sizes} placeholder"""
        renderer = TemplateRenderer()
        
        # Test combination sizes
        product_with_combinations = Mock(spec=Product)
        
        size = Mock(spec=Size)
        size.size_type = 'combination'
        size.combination_data = {
            '32': ['A', 'B'],
            '34': ['A', 'C']
        }
        size.deleted_at = None
        
        product_with_combinations.sizes = [size]
        product_with_combinations.id = 123
        product_with_combinations.name = 'Test Bra'
        product_with_combinations.sku = 'BRA-001'
        product_with_combinations.price = 49.99
        product_with_combinations.currency = 'USD'
        product_with_combinations.availability = 'In Stock'
        product_with_combinations.color = 'Black'
        product_with_combinations.composition = 'Cotton'
        product_with_combinations.item = 'Bra'
        product_with_combinations.store = 'Store'
        product_with_combinations.comment = 'Comment'
        product_with_combinations.product_url = 'http://example.com'
        product_with_combinations.created_at = datetime.now()
        product_with_combinations.images = []
        
        with patch('services.template_service.ProductSchema') as mock_schema:
            mock_instance = Mock()
            mock_instance.sell_price = 59.99
            mock_schema.model_validate.return_value = mock_instance
            
            data = renderer._get_product_data(product_with_combinations)
        
        # Should have leading newline for combination sizes
        assert data['sizes'].startswith('\n')
        assert '32: A, B' in data['sizes']
        assert '34: A, C' in data['sizes']
        
        # Test simple sizes - should NOT have leading newline
        product_with_simple = Mock(spec=Product)
        
        size1 = Mock(spec=Size)
        size1.size_type = 'simple'
        size1.size_value = 'M'
        size1.deleted_at = None
        
        size2 = Mock(spec=Size)
        size2.size_type = 'simple'
        size2.size_value = 'L'
        size2.deleted_at = None
        
        product_with_simple.sizes = [size1, size2]
        product_with_simple.id = 124
        product_with_simple.name = 'Test Shirt'
        product_with_simple.sku = 'SHIRT-001'
        product_with_simple.price = 29.99
        product_with_simple.currency = 'USD'
        product_with_simple.availability = 'In Stock'
        product_with_simple.color = 'Blue'
        product_with_simple.composition = 'Cotton'
        product_with_simple.item = 'Shirt'
        product_with_simple.store = 'Store'
        product_with_simple.comment = 'Comment'
        product_with_simple.product_url = 'http://example.com'
        product_with_simple.created_at = datetime.now()
        product_with_simple.images = []
        
        with patch('services.template_service.ProductSchema') as mock_schema:
            mock_instance = Mock()
            mock_instance.sell_price = 35.99
            mock_schema.model_validate.return_value = mock_instance
            
            data = renderer._get_product_data(product_with_simple)
        
        # Should NOT have leading newline for simple sizes
        assert not data['sizes'].startswith('\n')
        assert data['sizes'] == 'M, L'