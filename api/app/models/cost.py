from typing import Literal, get_args

from sqlalchemy import JSON, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

# The metered event kinds. CostType is the type; COST_TYPES derives the runtime tuple from
# it with get_args, so the two cannot drift (no StrEnum, per the quest's no-enum rule).
# `describer` is defined here but its write point ships with describe-code-blocks; only
# `firecrawl` and `tts` are written today.
CostType = Literal["firecrawl", "describer", "tts"]
COST_TYPES: tuple[CostType, ...] = get_args(CostType)


class CostEntry(Base):
    __tablename__ = "cost_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    item_id: Mapped[str] = mapped_column(String, ForeignKey("items.id"))
    type: Mapped[str] = mapped_column(String)
    # The raw measure (quantity + unit) never goes stale and re-prices against future rates;
    # dollars is snapshotted at write time so a total needs no price-table join. Keeping only
    # one loses one of those (see docs/quest-log/cost-ledger.md).
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String)
    dollars: Mapped[float] = mapped_column(Float)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
