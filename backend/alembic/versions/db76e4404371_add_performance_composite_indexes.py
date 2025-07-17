"""add_performance_composite_indexes

Revision ID: db76e4404371
Revises: a8b9c1d2e3f4
Create Date: 2025-07-17 21:08:39.872252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db76e4404371'
down_revision: Union[str, Sequence[str], None] = 'a8b9c1d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite indexes for frequently used query patterns."""
    # Add composite index for store and deleted_at filtering
    op.create_index(
        'idx_products_store_deleted_at',
        'products',
        ['store', 'deleted_at']
    )
    
    # Add composite index for price and currency filtering
    op.create_index(
        'idx_products_price_currency',
        'products', 
        ['price', 'currency']
    )
    
    # Add composite index for size type and value filtering
    op.create_index(
        'idx_sizes_type_value',
        'sizes',
        ['size_type', 'size_value']
    )


def downgrade() -> None:
    """Remove composite indexes."""
    # Remove composite indexes in reverse order
    op.drop_index('idx_sizes_type_value', table_name='sizes')
    op.drop_index('idx_products_price_currency', table_name='products')
    op.drop_index('idx_products_store_deleted_at', table_name='products')
