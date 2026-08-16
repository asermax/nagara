"""add cost_entries table

Revision ID: e5b1c9a742d0
Revises: a4e7f2b91c56
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b1c9a742d0'
down_revision: Union[str, None] = 'a4e7f2b91c56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One row per metered event, scoped to its item. quantity is Float because it spans both
    # integer credits and fractional audio-seconds; dollars is the snapshot priced at write
    # time; detail is type-specific extras (firecrawl destination + proxy, tts duration).
    op.create_table(
        'cost_entries',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('dollars', sa.Float(), nullable=False),
        sa.Column('detail', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['items.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('cost_entries')
