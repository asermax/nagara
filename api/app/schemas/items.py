from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from ..models.item import ItemStatus

# The three unit kinds. UNIT_TYPES is the canonical runtime list; UnitType is the
# pydantic discriminator kept in step with it (no StrEnum, per the project's no-enum rule).
UNIT_TYPES: tuple[str, ...] = ("paragraph", "code", "image")
UnitType = Literal["paragraph", "code", "image"]


class _UnitBase(BaseModel):
    # Timing is joined onto a unit at finalize; absent until the item is ready.
    index: int | None = None
    start: float | None = None
    end: float | None = None


class ParagraphUnit(_UnitBase):
    type: Literal["paragraph"]
    display: str
    spoken: str


class CodeUnit(_UnitBase):
    type: Literal["code"]
    display: str
    spoken: str


class ImageUnit(_UnitBase):
    type: Literal["image"]
    display: str
    spoken: str
    image: str


Unit = Annotated[Union[ParagraphUnit, CodeUnit, ImageUnit], Field(discriminator="type")]


class _UnitResponseBase(BaseModel):
    index: int
    display: str
    start: float
    end: float


class ParagraphResponse(_UnitResponseBase):
    type: Literal["paragraph"]


class CodeResponse(_UnitResponseBase):
    type: Literal["code"]


class ImageResponse(_UnitResponseBase):
    type: Literal["image"]
    image: str


# The wire element is the persisted unit with `spoken` projected out. The union mirrors the
# persisted one so `image` rides only on an image unit — a paragraph or code element carries
# no image key at all, not a null one.
UnitResponse = Annotated[
    Union[ParagraphResponse, CodeResponse, ImageResponse], Field(discriminator="type")
]


class CreateItemPayload(BaseModel):
    url: str
    voice: str | None = None


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str | None
    status: ItemStatus
    voice: str
    created_at: str
    duration: float | None
    units: list[UnitResponse] | None = None
    error: str | None

    @field_validator("units", mode="before")
    @classmethod
    def _hide_until_timed(cls, value):
        # Units are persisted at enqueue carrying type/display/spoken but no timing, and
        # gain their window at finalize. Only the timed shape is a wire element, so the
        # list is held back until the item is ready.
        if not value:
            return None
        first = value[0]
        if isinstance(first, dict) and first.get("start") is None:
            return None
        return value

    @computed_field
    @property
    def audio_url(self) -> str | None:
        return f"/items/{self.id}/audio" if self.status == ItemStatus.READY else None
