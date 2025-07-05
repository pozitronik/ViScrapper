"""fix_sku_unique_constraint_for_active_products

Revision ID: bd6cc0311453
Revises: f2e3d4c5b6a7
Create Date: 2025-07-05 09:01:53.892008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd6cc0311453'
down_revision: Union[str, Sequence[str], None] = 'f2e3d4c5b6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix SKU unique constraint for active products only."""
    # Drop the existing composite unique index
    op.drop_index('ix_products_sku_deleted_unique', table_name='products')
    
    # Create a partial unique index that only applies to active records (deleted_at IS NULL)
    # SQLite supports partial indexes with WHERE clause
    op.execute('CREATE UNIQUE INDEX ix_products_sku_active_unique ON products (sku) WHERE deleted_at IS NULL')


def downgrade() -> None:
    """Restore previous composite constraint."""
    # Drop the partial unique index
    op.drop_index('ix_products_sku_active_unique', table_name='products')
    
    # Recreate the composite unique index
    op.create_index('ix_products_sku_deleted_unique', 'products', ['sku', 'deleted_at'], unique=True)
