"""add_start_date_to_subscriptions

Revision ID: add_start_date_to_subscriptions
Revises: fca73b4d5834
Create Date: 2024-03-19 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision: str = 'add_start_date_to_subscriptions'
down_revision: Union[str, None] = 'fca73b4d5834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add start_date column with default value of CURRENT_TIMESTAMP
    op.add_column(
        'subscriptions',
        sa.Column(
            'start_date',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    
    # Update existing rows to set start_date equal to created_at
    op.execute(
        """
        UPDATE subscriptions 
        SET start_date = created_at
        """
    )


def downgrade() -> None:
    op.drop_column('subscriptions', 'start_date') 