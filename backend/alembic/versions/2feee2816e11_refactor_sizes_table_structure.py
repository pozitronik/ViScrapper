"""refactor_sizes_table_structure

Revision ID: 2feee2816e11
Revises: 1bd31889f287
Create Date: 2025-06-29 14:14:22.093504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2feee2816e11'
down_revision: Union[str, Sequence[str], None] = '1bd31889f287'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop and recreate sizes table with cleaner structure."""
    # Drop existing sizes table (will lose all data)
    op.drop_table('sizes')
    
    # Create new sizes table with cleaner structure
    op.create_table('sizes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('size_type', sa.String(), nullable=False),  # 'simple' or 'combination'
        sa.Column('size_value', sa.String(), nullable=True),  # For simple sizes: the size value (e.g., "M", "L")
        sa.Column('size1_type', sa.String(), nullable=True),  # For combinations: first size type (e.g., "Band")
        sa.Column('size2_type', sa.String(), nullable=True),  # For combinations: second size type (e.g., "Cup")
        sa.Column('combination_data', sa.JSON(), nullable=True),  # For combinations: {"34": ["B", "C"], "36": ["A"]}
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )


def downgrade() -> None:
    """Recreate old sizes table structure."""
    # Drop new sizes table
    op.drop_table('sizes')
    
    # Recreate old sizes table structure
    op.create_table('sizes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('size_type', sa.String(), nullable=True),
        sa.Column('size_combination_data', sa.JSON(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, index=True),
    )
