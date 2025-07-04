"""add selling_price field to products table

Revision ID: dc7dc0e455d4
Revises: 2feee2816e11
Create Date: 2025-07-04 19:59:33.914667

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7dc0e455d4'
down_revision: Union[str, Sequence[str], None] = '2feee2816e11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add selling_price column to products table
    op.add_column('products', sa.Column('selling_price', sa.Float(), nullable=True, comment='Manual override for selling price. If null, uses price modifier calculation'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove selling_price column from products table
    op.drop_column('products', 'selling_price')