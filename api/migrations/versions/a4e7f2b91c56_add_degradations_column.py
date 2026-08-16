"""add degradations column

Revision ID: a4e7f2b91c56
Revises: b8f2a1c4d7e3
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4e7f2b91c56'
down_revision: Union[str, None] = 'b8f2a1c4d7e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('degradations', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('degradations')
