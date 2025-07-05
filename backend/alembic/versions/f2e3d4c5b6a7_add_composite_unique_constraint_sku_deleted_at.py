"""Add composite unique constraint for sku and deleted_at

Revision ID: f2e3d4c5b6a7
Revises: e1f2b3c4d5e6
Create Date: 2025-07-05 08:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2e3d4c5b6a7'
down_revision = 'e1f2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    """Add composite unique constraint for (sku, deleted_at)."""
    # Drop the existing unique constraint on sku
    op.drop_index('ix_products_sku', table_name='products')
    
    # Create new index on sku (non-unique)
    op.create_index('ix_products_sku', 'products', ['sku'], unique=False)
    
    # Create composite unique index on (sku, deleted_at)
    op.create_index('ix_products_sku_deleted_unique', 'products', ['sku', 'deleted_at'], unique=True)


def downgrade():
    """Remove composite unique constraint and restore original sku unique constraint."""
    # Drop the composite unique index
    op.drop_index('ix_products_sku_deleted_unique', table_name='products')
    
    # Drop the non-unique sku index
    op.drop_index('ix_products_sku', table_name='products')
    
    # Recreate the original unique constraint on sku
    op.create_index('ix_products_sku', 'products', ['sku'], unique=True)