"""add item display column

Revision ID: 43f4ed0fcb35
Revises: c0552ec15944
Create Date: 2026-07-17 17:35:11.595080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43f4ed0fcb35'
down_revision: Union[str, None] = 'c0552ec15944'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('display', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('display')
