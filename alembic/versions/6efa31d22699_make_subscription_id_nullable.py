"""make_subscription_id_nullable

Revision ID: 6efa31d22699
Revises: add_start_date_to_subscriptions
Create Date: 2025-04-02 22:07:26.034457

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '6efa31d22699'
down_revision: Union[str, None] = 'add_start_date_to_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get the foreign key name from information_schema
    result = op.get_bind().execute(
        text("""
        SELECT CONSTRAINT_NAME 
        FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_NAME = 'payment_records' 
        AND COLUMN_NAME = 'subscription_id' 
        AND REFERENCED_TABLE_NAME = 'subscriptions'
        AND CONSTRAINT_SCHEMA = DATABASE()
        """)
    ).fetchone()
    
    if result:
        fk_name = result[0]
        # Drop the foreign key constraint
        op.drop_constraint(
            fk_name,
            "payment_records",
            type_="foreignkey"
        )
    
    # Modify the column to allow NULL values
    op.alter_column(
        "payment_records",
        "subscription_id",
        existing_type=sa.BigInteger(),
        nullable=True
    )
    
    # Re-add the foreign key constraint with ON DELETE CASCADE
    op.create_foreign_key(
        None,  # Let MySQL generate the constraint name
        "payment_records",
        "subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # First update any NULL subscription_ids (if any exist)
    op.execute(
        text("""
        DELETE FROM payment_records 
        WHERE subscription_id IS NULL
        """)
    )
    
    # Get the foreign key name from information_schema
    result = op.get_bind().execute(
        text("""
        SELECT CONSTRAINT_NAME 
        FROM information_schema.KEY_COLUMN_USAGE 
        WHERE TABLE_NAME = 'payment_records' 
        AND COLUMN_NAME = 'subscription_id' 
        AND REFERENCED_TABLE_NAME = 'subscriptions'
        AND CONSTRAINT_SCHEMA = DATABASE()
        """)
    ).fetchone()
    
    if result:
        fk_name = result[0]
        # Drop the foreign key constraint
        op.drop_constraint(
            fk_name,
            "payment_records",
            type_="foreignkey"
        )
    
    # Modify the column to not allow NULL values
    op.alter_column(
        "payment_records",
        "subscription_id",
        existing_type=sa.BigInteger(),
        nullable=False
    )
    
    # Re-add the foreign key constraint
    op.create_foreign_key(
        None,  # Let MySQL generate the constraint name
        "payment_records",
        "subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="CASCADE"
    )
