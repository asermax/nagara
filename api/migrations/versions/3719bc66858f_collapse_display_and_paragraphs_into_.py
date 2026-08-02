"""collapse display and paragraphs into units

Revision ID: 3719bc66858f
Revises: 43f4ed0fcb35
Create Date: 2026-08-02 19:53:07.415820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import JSON, Column, MetaData, String, Table, select, text, update


# revision identifiers, used by Alembic.
revision: str = '3719bc66858f'
down_revision: Union[str, None] = '43f4ed0fcb35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _items() -> Table:
    # A core Table over the live columns, so the JSON columns serialize per dialect for
    # the read-modify-write backfill rather than raw SQL that diverges SQLite/Postgres.
    return Table(
        "items",
        MetaData(),
        Column("id", String, primary_key=True),
        Column("display", JSON),
        Column("paragraphs", JSON),
        Column("units", JSON),
    )


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Drop the permanently stranded rows: status generating with no paragraphs to join a
    #    timeline onto. Match case-insensitively to catch the live casing drift.
    bind.execute(text("DELETE FROM items WHERE lower(status) = 'generating' AND paragraphs IS NULL"))

    # 2. Normalize the READY/ready casing drift that is live in both databases.
    bind.execute(text("UPDATE items SET status = lower(status)"))

    # 3. Add the merged column.
    op.add_column("items", sa.Column("units", sa.JSON(), nullable=True))

    # 4. Backfill one typed unit per existing window. Every old unit becomes a paragraph;
    #    display falls back to the spoken text for the three pre-display rows. index, start
    #    and end come across verbatim, so timing windows stay contiguous and the last end
    #    still equals the audio duration.
    items = _items()
    rows = bind.execute(
        select(items.c.id, items.c.display, items.c.paragraphs).where(items.c.paragraphs.is_not(None))
    )
    for item_id, display, paragraphs in rows:
        built = []
        for p in paragraphs or []:
            i = p["index"]
            display_text = display[i] if i < len(display or []) else p["text"]
            built.append(
                {
                    "index": i,
                    "type": "paragraph",
                    "display": display_text,
                    "spoken": p["text"],
                    "start": p["start"],
                    "end": p["end"],
                }
            )
        bind.execute(update(items).where(items.c.id == item_id).values(units=built))

    # 5. The old columns are now redundant.
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("display")
        batch_op.drop_column("paragraphs")


def downgrade() -> None:
    bind = op.get_bind()

    # Rebuild display and paragraphs from units. The five deleted generating rows cannot be
    # restored; status stays lowercase because the model now stores the enum by value.
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(sa.Column("display", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("paragraphs", sa.JSON(), nullable=True))

    items = _items()
    rows = bind.execute(select(items.c.id, items.c.units).where(items.c.units.is_not(None)))
    for item_id, units in rows:
        units = units or []
        display = [u.get("display", u.get("spoken", "")) for u in units]
        paragraphs = [
            {"index": u["index"], "start": u["start"], "end": u["end"], "text": u["spoken"]}
            for u in units
        ]
        bind.execute(
            update(items).where(items.c.id == item_id).values(display=display, paragraphs=paragraphs)
        )

    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("units")
