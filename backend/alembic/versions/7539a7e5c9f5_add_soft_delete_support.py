"""Add soft delete support

Revision ID: 7539a7e5c9f5
Revises: d7bf728a2f59
Create Date: 2025-06-27 04:04:51.367051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7539a7e5c9f5'
down_revision: Union[str, Sequence[str], None] = 'd7bf728a2f59'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add deleted_at column to products table
    op.add_column('products', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_products_deleted_at', 'products', ['deleted_at'])
    
    # Add deleted_at column to images table
    op.add_column('images', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_images_deleted_at', 'images', ['deleted_at'])
    
    # Add deleted_at column to sizes table
    op.add_column('sizes', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_sizes_deleted_at', 'sizes', ['deleted_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove indexes and columns in reverse order
    op.drop_index('ix_sizes_deleted_at', 'sizes')
    op.drop_column('sizes', 'deleted_at')
    
    op.drop_index('ix_images_deleted_at', 'images')
    op.drop_column('images', 'deleted_at')
    
    op.drop_index('ix_products_deleted_at', 'products')
    op.drop_column('products', 'deleted_at')
