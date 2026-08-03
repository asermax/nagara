"""queued lifecycle columns

Revision ID: b8f2a1c4d7e3
Revises: 3719bc66858f
Create Date: 2026-08-02 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8f2a1c4d7e3'
down_revision: Union[str, None] = '3719bc66858f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Three columns for the queued lifecycle, plus the `queued` status value. The status
    # column is a plain String with no CHECK constraint (see the initial schema), so the new
    # value needs no DDL: it is simply another string the column already accepts, stored
    # lowercase by the model's values_callable.
    #
    # queued_at / enriched_at are ISO strings, matching created_at. retry_count lands here so
    # the retry route ships in a later quest without a second revision; the column is unused
    # until then.
    op.add_column('items', sa.Column('queued_at', sa.String(), nullable=True))
    op.add_column('items', sa.Column('enriched_at', sa.String(), nullable=True))
    op.add_column('items', sa.Column('retry_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('items') as batch_op:
        batch_op.drop_column('retry_count')
        batch_op.drop_column('enriched_at')
        batch_op.drop_column('queued_at')
