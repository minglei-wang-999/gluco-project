"""add_weixin_users_table

Revision ID: 73301f8ec277
Revises: 2d07c98c0046
Create Date: 2024-01-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '73301f8ec277'
down_revision: Union[str, None] = '2d07c98c0046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create weixin_users table
    op.create_table(
        'weixin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('openid', sa.String(100), nullable=False),
        sa.Column('nickname', sa.String(100), nullable=True),
        sa.Column('avatar_url', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weixin_users_id'), 'weixin_users', ['id'], unique=False)
    op.create_index(op.f('ix_weixin_users_openid'), 'weixin_users', ['openid'], unique=True)
    
    # Update nutrition_records table
    op.add_column('nutrition_records', sa.Column('weixin_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_nutrition_records_weixin_user_id',
        'nutrition_records', 'weixin_users',
        ['weixin_user_id'], ['id']
    )
    op.alter_column('nutrition_records', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    # Remove foreign key from nutrition_records
    op.drop_constraint('fk_nutrition_records_weixin_user_id', 'nutrition_records', type_='foreignkey')
    op.drop_column('nutrition_records', 'weixin_user_id')
    op.alter_column('nutrition_records', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=False)
    
    # Drop weixin_users table
    op.drop_index(op.f('ix_weixin_users_openid'), table_name='weixin_users')
    op.drop_index(op.f('ix_weixin_users_id'), table_name='weixin_users')
    op.drop_table('weixin_users')
