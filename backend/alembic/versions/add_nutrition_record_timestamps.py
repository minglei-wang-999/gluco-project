"""add timestamp columns to nutrition_records

Revision ID: add_nutrition_record_timestamps
Revises: update_ingredients_columns
Create Date: 2024-01-24 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = 'add_nutrition_record_timestamps'
down_revision: Union[str, None] = 'update_ingredients_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add missing columns for nutrition analysis
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('nutrition_records')]
    
    columns_to_add = [
        ('total_carbs', sa.Float(), True),
        ('total_protein', sa.Float(), True),
        ('total_fat', sa.Float(), True),
        ('total_gl', sa.Float(), True),
        ('meal_gl_category', sa.String(50), True),
        ('impact_level', sa.String(50), True),
        ('protein_level', sa.String(50), True),
        ('fat_level', sa.String(50), True),
        ('protein_explanation', sa.String(500), True),
        ('fat_explanation', sa.String(500), True),
        ('impact_explanation', sa.String(500), True),
        ('best_time', sa.String(100), True)
    ]
    
    for col_name, col_type, nullable in columns_to_add:
        if col_name not in existing_columns:
            op.add_column('nutrition_records', sa.Column(col_name, col_type, nullable=nullable))

def downgrade() -> None:
    # Remove added columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('nutrition_records')]
    
    columns_to_drop = [
        'best_time',
        'impact_explanation',
        'fat_explanation',
        'protein_explanation',
        'fat_level',
        'protein_level',
        'impact_level',
        'meal_gl_category',
        'total_gl',
        'total_fat',
        'total_protein',
        'total_carbs'
    ]
    
    for col_name in columns_to_drop:
        if col_name in existing_columns:
            op.drop_column('nutrition_records', col_name) 