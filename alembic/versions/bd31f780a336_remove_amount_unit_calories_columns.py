"""remove_amount_unit_calories_columns

Revision ID: bd31f780a336
Revises: 6efa31d22699
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "bd31f780a336"
down_revision = "6efa31d22699"
branch_labels = None
depends_on = None


def upgrade():
    # Drop columns: amount, unit, calories
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_column("amount")
        batch_op.drop_column("unit")
        batch_op.drop_column("calories")


def downgrade():
    # Add back columns: amount, unit, calories
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.add_column(sa.Column("amount", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("unit", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("calories", sa.Float(), nullable=True))
