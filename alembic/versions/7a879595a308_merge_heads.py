"""merge heads

Revision ID: 7a879595a308
Revises: 73301f8ec277, bfdb2c64efc4
Create Date: 2025-01-26 14:59:34.834815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a879595a308'
down_revision: Union[str, None] = ('73301f8ec277', 'bfdb2c64efc4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
