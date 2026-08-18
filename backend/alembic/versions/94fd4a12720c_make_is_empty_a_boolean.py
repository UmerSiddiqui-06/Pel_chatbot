"""make is_empty a boolean

Revision ID: 94fd4a12720c
Revises: 54bd41a9dde0
Create Date: 2026-08-18 12:49:03.955647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94fd4a12720c'
down_revision: Union[str, Sequence[str], None] = '54bd41a9dde0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('messages', 'is_empty')
    op.add_column('messages', sa.Column('is_empty', sa.Boolean(), nullable=False, server_default='false'))
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column('messages', 'is_empty')
    op.add_column('messages', sa.Column('is_empty', sa.VARCHAR(), nullable=True))
    # ### end Alembic commands ###
