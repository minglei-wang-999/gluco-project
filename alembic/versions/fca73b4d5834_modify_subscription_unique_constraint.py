"""modify_subscription_unique_constraint

Revision ID: fca73b4d5834
Revises: 342a0f239c84
Create Date: 2024-03-19 16:35:01.598013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fca73b4d5834'
down_revision: Union[str, None] = '342a0f239c84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old unique index on user_id
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    
    # Create a new non-unique index on user_id for performance
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    
    # Create a composite unique index on user_id and status
    # This ensures a user can only have one subscription in each status
    op.create_index(
        "ix_subscriptions_user_id_status",
        "subscriptions",
        ["user_id", "status"],
        unique=True
    )


def downgrade() -> None:
    # Drop the composite unique index
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    
    # Drop the non-unique index on user_id
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    
    # Recreate the original unique index on user_id
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
