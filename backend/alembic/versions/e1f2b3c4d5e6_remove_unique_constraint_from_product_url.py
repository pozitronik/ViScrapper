"""Remove unique constraint from product_url

Revision ID: e1f2b3c4d5e6
Revises: dc7dc0e455d4
Create Date: 2025-07-05 08:30:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e1f2b3c4d5e6'
down_revision = 'dc7dc0e455d4'
branch_labels = None
depends_on = None


def upgrade():
    """Remove unique constraint from product_url column."""
    # Drop the unique constraint/index on product_url
    op.drop_index('ix_products_product_url', table_name='products')
    
    # Recreate the index without unique constraint
    op.create_index('ix_products_product_url', 'products', ['product_url'], unique=False)


def downgrade():
    """Restore unique constraint to product_url column."""
    # Drop the non-unique index
    op.drop_index('ix_products_product_url', table_name='products')
    
    # Recreate the unique index
    op.create_index('ix_products_product_url', 'products', ['product_url'], unique=True)