from enum import StrEnum

from sqlalchemy import JSON, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class ItemStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[ItemStatus] = mapped_column(Enum(ItemStatus, native_enum=False))
    voice: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_format: Mapped[str | None] = mapped_column(String, nullable=True)
    display: Mapped[list | None] = mapped_column(JSON, nullable=True)  # markdown units awaiting timing
    paragraphs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    modal_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
