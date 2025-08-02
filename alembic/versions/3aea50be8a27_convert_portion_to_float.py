"""convert_portion_to_float

Revision ID: 3aea50be8a27
Revises: bd31f780a336
Create Date: 2024-03-19 10:00:30.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "3aea50be8a27"
down_revision = "bd31f780a336"
branch_labels = None
depends_on = None


def upgrade():
    # Alter column type to FLOAT - MySQL will automatically convert the numeric strings
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.alter_column("portion",
                            existing_type=sa.String(100),
                            type_=sa.Float(),
                            existing_nullable=True)


def downgrade():
    # Alter column type back to VARCHAR - MySQL will automatically convert the numbers to strings
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.alter_column("portion",
                            existing_type=sa.Float(),
                            type_=sa.String(100),
                            existing_nullable=True)
