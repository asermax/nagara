from enum import StrEnum

from sqlalchemy import JSON, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class ItemStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


# Store the enum by value, not name: the migration lowercases live status rows, and this
# keeps new writes lowercase too so the READY/ready casing drift does not return.
_STATUS_ENUM = Enum(ItemStatus, native_enum=False, values_callable=lambda e: [m.value for m in e])


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ItemStatus] = mapped_column(_STATUS_ENUM)
    voice: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_format: Mapped[str | None] = mapped_column(String, nullable=True)
    units: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    modal_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # The lifecycle clock and the retry bound. queued_at is set when the background task
    # begins and rewritten on every retry, so the ceiling measures work age rather than
    # wall age (created_at never moves and would make a retried item instantly stale).
    # enriched_at marks every unit resolved. retry_count lands here but the retry route is
    # a sibling quest, so the column ships unused.
    queued_at: Mapped[str | None] = mapped_column(String, nullable=True)
    enriched_at: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    degradations: Mapped[list | None] = mapped_column(JSON, nullable=True)
