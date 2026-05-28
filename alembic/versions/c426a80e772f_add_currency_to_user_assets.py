"""add_currency_to_user_assets

Revision ID: c426a80e772f
Revises: 4a67f12ac9d3
Create Date: 2026-05-16 14:53:04.476842

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c426a80e772f'
down_revision: Union[str, Sequence[str], None] = '4a67f12ac9d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add currency column with default IDR
    op.add_column('user_assets', sa.Column('currency', sa.String(length=3), nullable=False, server_default='IDR'))
    
    # Update existing records based on asset_type
    op.execute("""
        UPDATE user_assets 
        SET currency = CASE 
            WHEN asset_type IN ('crypto', 'stock_us') THEN 'USD'
            WHEN asset_type IN ('stock_id', 'gold') THEN 'IDR'
            WHEN asset_type = 'cash' THEN UPPER(symbol)
            ELSE 'IDR'
        END
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_assets', 'currency')
