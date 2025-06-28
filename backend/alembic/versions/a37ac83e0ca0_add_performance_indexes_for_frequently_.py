"""Add performance indexes for frequently queried fields

Revision ID: a37ac83e0ca0
Revises: 94f0296b0c17
Create Date: 2025-06-28 04:49:41.973063

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a37ac83e0ca0'
down_revision: Union[str, Sequence[str], None] = '94f0296b0c17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for frequently queried fields."""
    # Create composite index for products filtering by availability and color
    op.create_index('idx_products_availability_color', 'products', ['availability', 'color'])
    
    # Create index for products filtering by currency
    op.create_index('idx_products_currency', 'products', ['currency'])
    
    # Create index for products filtering by item type
    op.create_index('idx_products_item', 'products', ['item'])
    
    # Create composite index for filtering active products (not deleted)
    op.create_index('idx_products_active', 'products', ['deleted_at', 'created_at'])
    
    # Create index for telegram posting status
    op.create_index('idx_products_telegram_posted', 'products', ['telegram_posted_at'])
    
    # Create composite index for images by product and active status
    op.create_index('idx_images_product_active', 'images', ['product_id', 'deleted_at'])
    
    # Create composite index for sizes by product and active status
    op.create_index('idx_sizes_product_active', 'sizes', ['product_id', 'deleted_at'])
    
    # Create index for image URLs for faster duplicate checking
    op.create_index('idx_images_url', 'images', ['url'])


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_images_url', 'images')
    op.drop_index('idx_sizes_product_active', 'sizes')
    op.drop_index('idx_images_product_active', 'images')
    op.drop_index('idx_products_telegram_posted', 'products')
    op.drop_index('idx_products_active', 'products')
    op.drop_index('idx_products_item', 'products')
    op.drop_index('idx_products_currency', 'products')
    op.drop_index('idx_products_availability_color', 'products')
