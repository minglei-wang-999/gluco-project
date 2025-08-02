"""make meal fields nullable

Revision ID: bfdb2c64efc4
Revises: add_nutrition_record_timestamps
Create Date: 2024-01-24 21:42:42.897644

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bfdb2c64efc4'
down_revision: Union[str, None] = 'add_nutrition_record_timestamps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Make meal_type and meal_time columns nullable
    with op.batch_alter_table('nutrition_records') as batch_op:
        batch_op.alter_column('meal_type',
                    existing_type=sa.String(50),
                    nullable=True)
        batch_op.alter_column('meal_time',
                    existing_type=sa.DateTime(),
                    nullable=True)

def downgrade() -> None:
    # Revert meal_type and meal_time columns to be non-nullable
    with op.batch_alter_table('nutrition_records') as batch_op:
        batch_op.alter_column('meal_type',
                    existing_type=sa.String(50),
                    nullable=False)
        batch_op.alter_column('meal_time',
                    existing_type=sa.DateTime(),
                    nullable=False)
