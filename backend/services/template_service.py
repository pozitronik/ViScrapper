"""
Template rendering service for message templates with placeholder replacement.
Supports dynamic placeholder replacement using product data.
"""

import re
from typing import Dict, List, Any, Tuple, Optional, cast
from datetime import datetime
from sqlalchemy.orm import Session

from models.product import Product
from crud.product import get_product_by_id
from crud.template import get_template_by_id
from utils.logger import get_logger
from exceptions.base import ValidationException
from schemas.product import Product as ProductSchema

logger = get_logger(__name__)


class TemplateRenderer:
    """Handles template rendering with placeholder replacement"""

    # Define available placeholders and their descriptions
    AVAILABLE_PLACEHOLDERS = {
        # Short format (user-friendly)
        '{name}': 'Product name',
        '{sku}': 'Product SKU',
        '{price}': 'Product price',
        '{sell_price}': 'Product sell price (calculated)',
        '{currency}': 'Product currency',
        '{availability}': 'Product availability status',
        '{color}': 'Product color',
        '{composition}': 'Product composition',
        '{item}': 'Product item type',
        '{store}': 'Store or brand name',
        '{comment}': 'Product comment',
        '{url}': 'Product URL',
        '{id}': 'Product ID',
        '{created_at}': 'Product creation date',
        '{images_count}': 'Number of product images',
        '{sizes_count}': 'Number of available sizes',
        '{sizes}': 'Available sizes (comma-separated)',
        '{size}': 'Size information (formatted for display)',
        '{images}': 'Image URLs (comma-separated)',
        # Long format (backwards compatibility)
        '{product_name}': 'Product name',
        '{product_sku}': 'Product SKU',
        '{product_price}': 'Product price',
        '{product_sell_price}': 'Product sell price (calculated)',
        '{product_currency}': 'Product currency',
        '{product_availability}': 'Product availability status',
        '{product_color}': 'Product color',
        '{product_composition}': 'Product composition',
        '{product_item}': 'Product item type',
        '{product_store}': 'Store or brand name',
        '{product_comment}': 'Product comment',
        '{product_url}': 'Product URL',
        '{product_id}': 'Product ID',
        '{product_created_at}': 'Product creation date',
        '{product_images_count}': 'Number of product images',
        '{product_sizes_count}': 'Number of available sizes',
        '{product_sizes}': 'Available sizes (comma-separated)',
        '{product_size}': 'Size information (formatted for display)',
        '{product_images}': 'Image URLs (comma-separated)',
        # Date/time placeholders
        '{current_date}': 'Current date (YYYY-MM-DD)',
        '{current_time}': 'Current time (HH:MM:SS)',
        '{current_datetime}': 'Current date and time',
    }

    def __init__(self) -> None:
        self.placeholder_pattern = re.compile(r'\{([^}]+)\}')

    def get_available_placeholders(self) -> List[str]:
        """Get list of all available placeholder variables"""
        return list(self.AVAILABLE_PLACEHOLDERS.keys())

    def get_placeholder_descriptions(self) -> Dict[str, str]:
        """Get mapping of placeholders to their descriptions"""
        return self.AVAILABLE_PLACEHOLDERS.copy()

    def extract_placeholders(self, template_content: str) -> List[str]:
        """Extract all placeholders found in template content"""
        placeholders = self.placeholder_pattern.findall(template_content)
        return [f'{{{placeholder}}}' for placeholder in placeholders]

    def validate_placeholders(self, template_content: str) -> List[str]:
        """Validate placeholders in template content and return any invalid ones"""
        found_placeholders = self.extract_placeholders(template_content)
        available_placeholders = set(self.AVAILABLE_PLACEHOLDERS.keys())

        invalid_placeholders = []
        for placeholder in found_placeholders:
            if placeholder not in available_placeholders:
                invalid_placeholders.append(placeholder)

        return invalid_placeholders

    def _format_sizes_for_display(self, product: Product) -> Tuple[str, List[str], str]:
        """
        Format sizes for display, handling both simple sizes and combinations.
        
        Args:
            product: Product with sizes
            
        Returns:
            Tuple of (formatted_display_string, all_sizes_for_list, multiline_format_string)
        """
        if not product.sizes:
            return 'None', [], 'None'

        active_sizes = [size for size in product.sizes if size.deleted_at is None]
        if not active_sizes:
            return 'None', [], 'None'

        simple_sizes = []
        all_sizes_for_list = []
        combinations_found = False
        formatted_parts = []

        for size in active_sizes:
            if size.size_type == 'combination' and size.combination_data:
                # Handle size combinations
                combinations_found = True
                combo_lines = []

                # Sort size1 values for consistent display
                sorted_combinations = dict(sorted(size.combination_data.items()))

                for size1, size2_options in sorted_combinations.items():
                    # Format: "32: A B D"
                    size2_str = ' '.join(size2_options)
                    combo_lines.append(f"{size1}: {size2_str}")

                    # For the {sizes} placeholder, create individual size combinations
                    for size2 in size2_options:
                        all_sizes_for_list.append(f"{size1}{size2}")

                formatted_parts.append('\n'.join(combo_lines))
            elif size.size_type == 'simple' and size.size_value:
                # Handle simple sizes
                simple_sizes.append(size.size_value)
                all_sizes_for_list.append(size.size_value)

        # Build display string for {size} placeholder (without headers)
        if combinations_found and formatted_parts:
            if simple_sizes:
                # Mix of combinations and simple sizes
                display_str = f"{chr(10).join(formatted_parts)}\n{', '.join(simple_sizes)}"
            else:
                # Only combinations (no header)
                display_str = chr(10).join(formatted_parts)
        elif simple_sizes:
            # Only simple sizes
            display_str = ', '.join(simple_sizes)
        else:
            display_str = 'None'

        # Create multiline format for Telegram
        multiline_format = self._create_sizes_multiline(all_sizes_for_list, combinations_found, simple_sizes, active_sizes)

        return display_str, all_sizes_for_list, multiline_format

    def _create_sizes_multiline(self, all_sizes_for_list: List[str], combinations_found: bool, simple_sizes: List[str], active_sizes) -> str:
        """
        Create a multiline format for sizes with each band size on a new line.
        
        Args:
            all_sizes_for_list: List of all individual sizes
            combinations_found: Whether combination sizes were found
            simple_sizes: List of simple sizes
            active_sizes: List of active size objects
            
        Returns:
            Formatted string with each band size on a new line
        """
        if not all_sizes_for_list:
            return 'None'

        # For combination sizes (like bras), create multiline format
        if combinations_found:
            # Extract combination data from active sizes
            combination_data = {}
            for size in active_sizes:
                if size.size_type == 'combination' and size.combination_data:
                    combination_data.update(size.combination_data)

            if combination_data:
                # Sort size1 values (band sizes)
                sorted_size1 = sorted(combination_data.keys(), key=lambda x: (int(x) if x.isdigit() else float('inf'), x))

                # Create lines for each band size
                lines = []
                for size1 in sorted_size1:
                    size2_options = combination_data.get(size1, [])
                    if size2_options:
                        # Sort cup sizes and join with commas
                        sorted_cups = sorted(size2_options)
                        cups_str = ', '.join(sorted_cups)
                        lines.append(f"{size1}: {cups_str}")

                return '\n'.join(lines)

        # Fallback: return comma-separated list (should not be reached due to logic in _get_product_data)
        return ', '.join(all_sizes_for_list)

    def _get_product_data(self, product: Product) -> Dict[str, Any]:
        """Extract product data for placeholder replacement"""
        # Get sizes and format for display
        sizes_display, all_sizes_for_list, sizes_multiline = self._format_sizes_for_display(product)

        # Use multiline format only for combination sizes, comma-separated for simple sizes
        has_combinations = any(size.size_type == 'combination' for size in product.sizes if size.deleted_at is None) if product.sizes else False
        if has_combinations:
            # Add line break before combination sizes for proper template formatting
            sizes_str = f"\n{sizes_multiline}" if sizes_multiline != 'None' else 'None'
        else:
            sizes_str = ', '.join(all_sizes_for_list) if all_sizes_for_list else 'None'

        # Get images as comma-separated string
        images = [image.url for image in product.images if image.deleted_at is None] if product.images else []
        images_str = ', '.join(images) if images else 'None'

        # Format creation date
        created_at_str = product.created_at.strftime('%Y-%m-%d %H:%M:%S') if product.created_at else 'Unknown'

        # Get sell price using Pydantic schema's computed field
        try:
            # Create Pydantic object to use computed sell_price property
            product_schema = ProductSchema.model_validate(product)
            sell_price: Optional[float] = cast(Optional[float], product_schema.sell_price)
        except Exception as e:
            logger.warning(f"Failed to create ProductSchema for sell_price calculation: {e}")
            sell_price = None

        # Format sell price without unnecessary decimal zeros
        def format_price(price: Optional[float]) -> str:
            if price is None:
                return '0'
            # Remove trailing zeros and decimal point if it's a whole number
            formatted = f"{float(price):g}"
            return formatted

        # Return both short and long format for compatibility
        product_data = {
            # Short format (user-friendly)
            'name': product.name or 'Unnamed Product',
            'sku': product.sku or 'No SKU',
            'price': str(product.price) if product.price is not None else '0.00',
            'sell_price': format_price(sell_price),
            'currency': product.currency or 'USD',
            'availability': product.availability or 'Unknown',
            'color': product.color or 'Not specified',
            'composition': product.composition or 'Not specified',
            'item': product.item or 'Not specified',
            'store': product.store or 'Unknown Store',
            'comment': product.comment or '',
            'url': product.product_url or '',
            'id': str(product.id),
            'created_at': created_at_str,
            'images_count': str(len(images)),
            'sizes_count': str(len(all_sizes_for_list)),
            'sizes': sizes_str,
            'size': sizes_display,
            'images': images_str,
            # Long format (backwards compatibility)
            'product_name': product.name or 'Unnamed Product',
            'product_sku': product.sku or 'No SKU',
            'product_price': str(product.price) if product.price is not None else '0.00',
            'product_sell_price': format_price(sell_price),
            'product_currency': product.currency or 'USD',
            'product_availability': product.availability or 'Unknown',
            'product_color': product.color or 'Not specified',
            'product_composition': product.composition or 'Not specified',
            'product_item': product.item or 'Not specified',
            'product_store': product.store or 'Unknown Store',
            'product_comment': product.comment or '',
            'product_url': product.product_url or '',
            'product_id': str(product.id),
            'product_created_at': created_at_str,
            'product_images_count': str(len(images)),
            'product_sizes_count': str(len(all_sizes_for_list)),
            'product_sizes': sizes_str,
            'product_size': sizes_display,
            'product_images': images_str,
        }

        return product_data

    def _get_current_data(self) -> Dict[str, str]:
        """Get current date/time data for placeholder replacement"""
        now = datetime.now()
        return {
            'current_date': now.strftime('%Y-%m-%d'),
            'current_time': now.strftime('%H:%M:%S'),
            'current_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def render_template(self, template_content: str, product: Product) -> str:
        """
        Render template content by replacing placeholders with product data.
        
        Args:
            template_content: Template content with placeholders
            product: Product instance to get data from
            
        Returns:
            Rendered template content with placeholders replaced
            
        Raises:
            ValidationException: If template contains invalid placeholders
        """
        logger.debug(f"Rendering template for product ID: {product.id}")

        # Validate placeholders first
        invalid_placeholders = self.validate_placeholders(template_content)
        if invalid_placeholders:
            raise ValidationException(
                message="Template contains invalid placeholders",
                details={
                    "invalid_placeholders": invalid_placeholders,
                    "available_placeholders": list(self.AVAILABLE_PLACEHOLDERS.keys())
                }
            )

        # Get replacement data
        product_data = self._get_product_data(product)
        current_data = self._get_current_data()

        # Combine all replacement data
        replacement_data = {**product_data, **current_data}

        # Perform replacement
        rendered_content = template_content
        for placeholder, value in replacement_data.items():
            placeholder_key = f'{{{placeholder}}}'
            if placeholder_key in rendered_content:
                rendered_content = rendered_content.replace(placeholder_key, str(value))
                logger.debug(f"Replaced {placeholder_key} with: {value}")

        logger.debug("Template rendering completed successfully")
        return rendered_content

    def preview_template(self, template_content: str, product: Product) -> Dict[str, Any]:
        """
        Preview template rendering and return result with metadata.
        
        Args:
            template_content: Template content to preview
            product: Product instance to use for preview
            
        Returns:
            Dictionary with rendered content and metadata
        """
        logger.info(f"Previewing template with product ID: {product.id}")

        try:
            rendered_content = self.render_template(template_content, product)

            return {
                "rendered_content": rendered_content,
                "available_placeholders": self.get_available_placeholders(),
                "used_placeholders": self.extract_placeholders(template_content),
                "product_name": product.name,
                "product_id": product.id
            }

        except Exception as e:
            logger.error(f"Error previewing template: {e}")
            raise


# Create global template renderer instance
template_renderer = TemplateRenderer()


def render_template_with_product(
        db: Session,
        template_id: int,
        product_id: int
) -> Dict[str, Any]:
    """
    Render a template with a specific product.
    
    Args:
        db: Database session
        template_id: ID of the template to render
        product_id: ID of the product to use for rendering
        
    Returns:
        Dictionary with rendered content and metadata
        
    Raises:
        ValidationException: If template or product not found
    """
    logger.info(f"Rendering template ID {template_id} with product ID {product_id}")

    # Get template
    template = get_template_by_id(db, template_id)
    if not template:
        raise ValidationException(
            message="Template not found",
            details={"template_id": template_id}
        )

    if not template.is_active:
        raise ValidationException(
            message="Template is not active",
            details={"template_id": template_id, "is_active": False}
        )

    # Get product
    product = get_product_by_id(db, product_id)
    if not product:
        raise ValidationException(
            message="Product not found",
            details={"product_id": product_id}
        )

    # Render template
    rendered_content = template_renderer.render_template(str(template.template_content), product)

    return {
        "template_id": template.id,
        "template_name": template.name,
        "rendered_content": rendered_content,
        "product_id": product.id,
        "product_name": product.name,
        "product_url": product.product_url
    }


def preview_template_with_product(
        db: Session,
        template_content: str,
        product_id: int
) -> Dict[str, Any]:
    """
    Preview template content with a specific product.
    
    Args:
        db: Database session
        template_content: Template content to preview
        product_id: ID of the product to use for preview
        
    Returns:
        Dictionary with preview results
        
    Raises:
        ValidationException: If product not found
    """
    logger.info(f"Previewing template content with product ID {product_id}")

    # Get product
    product = get_product_by_id(db, product_id)
    if not product:
        raise ValidationException(
            message="Product not found",
            details={"product_id": product_id}
        )

    # Preview template
    return template_renderer.preview_template(template_content, product)


def get_template_placeholders() -> Dict[str, str]:
    """Get all available template placeholders with descriptions"""
    return template_renderer.get_placeholder_descriptions()


def validate_template_content(template_content: str) -> Dict[str, Any]:
    """
    Validate template content and return validation results.
    
    Args:
        template_content: Template content to validate
        
    Returns:
        Dictionary with validation results
    """
    invalid_placeholders = template_renderer.validate_placeholders(template_content)
    used_placeholders = template_renderer.extract_placeholders(template_content)

    return {
        "is_valid": len(invalid_placeholders) == 0,
        "invalid_placeholders": invalid_placeholders,
        "used_placeholders": used_placeholders,
        "available_placeholders": template_renderer.get_available_placeholders()
    }
