"""add the extraction boundary: recipe versions and item handle columns

Revision ID: d6c3f8a91b42
Revises: e5b1c9a742d0
Create Date: 2026-09-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6c3f8a91b42'
down_revision: Union[str, None] = 'e5b1c9a742d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # One row per version of one domain's recipe; the unique (domain, version) pair is
    # the index the current-version descent reads. The three item columns are all
    # nullable: rows persisted before the boundary existed carry none of them and stay
    # readable unchanged, with the nulls reading as absent (pre-deploy generating items
    # resolve their in-flight TTS call on poll, pre-deploy queued items complete the old
    # way without a spawn).
    op.create_table(
        'recipe_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('script', sa.Text(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('domain', 'version', name='uq_recipe_versions_domain_version'),
    )
    # Batch mode: SQLite cannot add a foreign key to an existing table in place, and
    # render_as_batch recreates it, which the three nullable columns tolerate.
    with op.batch_alter_table('items') as batch:
        batch.add_column(sa.Column('extraction_handle', sa.String(), nullable=True))
        batch.add_column(sa.Column('extraction_domain', sa.String(), nullable=True))
        batch.add_column(sa.Column('recipe_version_id', sa.String(), nullable=True))
        batch.create_foreign_key(
            'fk_items_recipe_version_id', 'recipe_versions', ['recipe_version_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('items') as batch:
        batch.drop_constraint('fk_items_recipe_version_id', type_='foreignkey')
        batch.drop_column('recipe_version_id')
        batch.drop_column('extraction_domain')
        batch.drop_column('extraction_handle')
    op.drop_table('recipe_versions')
