"""Add store column to products table

Revision ID: a8b9c1d2e3f4
Revises: f2e3d4c5b6a7
Create Date: 2025-07-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c1d2e3f4'
down_revision: Union[str, Sequence[str], None] = 'bd6cc0311453'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add store column to products table."""
    # Add store column with default value for existing records
    op.add_column('products', sa.Column(
        'store', 
        sa.String(length=100), 
        nullable=False, 
        server_default='Unknown Store',
        comment='Store or brand name (e.g., "Victoria\'s Secret", "Calvin Klein")'
    ))
    
    # Create index on store column for filtering performance
    op.create_index('ix_products_store', 'products', ['store'], unique=False)


def downgrade() -> None:
    """Remove store column from products table."""
    # Drop the index first
    op.drop_index('ix_products_store', table_name='products')
    
    # Remove store column
    op.drop_column('products', 'store')