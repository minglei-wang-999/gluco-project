"""rename_and_transform_nutrient_columns

Revision ID: 4d410bf1fb1a
Revises: 3aea50be8a27
Create Date: 2024-03-19 10:01:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = "4d410bf1fb1a"
down_revision = "3aea50be8a27"
branch_labels = None
depends_on = None


def upgrade():
    # First, add new columns
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.add_column(sa.Column("carbs_per_100g", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("protein_per_100g", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("fat_per_100g", sa.Float(), nullable=True))

    # Update the values in the new columns
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE ingredients 
        SET carbs_per_100g = carbs * 100 / portion,
            protein_per_100g = protein * 100 / portion,
            fat_per_100g = fat * 100 / portion
        WHERE portion IS NOT NULL AND portion > 0
    """))

    # Copy over values for rows without portion information
    conn.execute(text("""
        UPDATE ingredients 
        SET carbs_per_100g = carbs,
            protein_per_100g = protein,
            fat_per_100g = fat
        WHERE portion IS NULL OR portion = 0
    """))

    # Drop old columns
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_column("carbs")
        batch_op.drop_column("protein")
        batch_op.drop_column("fat")


def downgrade():
    # First, add back old columns
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.add_column(sa.Column("carbs", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("protein", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("fat", sa.Float(), nullable=True))

    # Convert values back
    conn = op.get_bind()
    conn.execute(text("""
        UPDATE ingredients 
        SET carbs = carbs_per_100g * portion / 100,
            protein = protein_per_100g * portion / 100,
            fat = fat_per_100g * portion / 100
        WHERE portion IS NOT NULL AND portion > 0
    """))

    # Copy over values for rows without portion information
    conn.execute(text("""
        UPDATE ingredients 
        SET carbs = carbs_per_100g,
            protein = protein_per_100g,
            fat = fat_per_100g
        WHERE portion IS NULL OR portion = 0
    """))

    # Drop new columns
    with op.batch_alter_table("ingredients") as batch_op:
        batch_op.drop_column("carbs_per_100g")
        batch_op.drop_column("protein_per_100g")
        batch_op.drop_column("fat_per_100g")
