"""update ingredients columns

Revision ID: update_ingredients_columns
Revises: add_user_columns
Create Date: 2024-01-24 10:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'update_ingredients_columns'
down_revision: Union[str, None] = 'add_user_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Rename carbohydrates to carbs
    op.alter_column('ingredients', 'carbohydrates',
                    new_column_name='carbs',
                    existing_type=sa.Float(),
                    existing_nullable=True)
    
    # Add new columns
    op.add_column('ingredients', sa.Column('gi', sa.Float(), nullable=True))
    op.add_column('ingredients', sa.Column('gl', sa.Float(), nullable=True))
    op.add_column('ingredients', sa.Column('gi_category', sa.String(50), nullable=True))
    op.add_column('ingredients', sa.Column('portion', sa.String(100), nullable=True))

def downgrade() -> None:
    # Remove added columns
    op.drop_column('ingredients', 'portion')
    op.drop_column('ingredients', 'gi_category')
    op.drop_column('ingredients', 'gl')
    op.drop_column('ingredients', 'gi')
    
    # Rename carbs back to carbohydrates
    op.alter_column('ingredients', 'carbs',
                    new_column_name='carbohydrates',
                    existing_type=sa.Float(),
                    existing_nullable=True) 