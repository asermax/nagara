from pydantic import BaseModel, ConfigDict, computed_field


class Paragraph(BaseModel):
    index: int
    start: float
    end: float
    text: str


class CreateItemPayload(BaseModel):
    url: str
    voice: str | None = None


class ItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    url: str
    title: str | None
    status: str
    voice: str
    created_at: str
    duration: float | None
    paragraphs: list[Paragraph] | None
    error: str | None

    @computed_field
    @property
    def audio_url(self) -> str | None:
        return f"/items/{self.id}/audio" if self.status == "ready" else None
