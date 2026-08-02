from pydantic import BaseModel


class Paragraph(BaseModel):
    # A timed window the Modal TTS service hands back: its index, its audio window, and
    # the spoken text synthesized for it. The text is a join key for timing, not the wire
    # shape — clients see the typed units in schemas/items.py with `spoken` filtered out.
    index: int
    start: float
    end: float
    text: str


class SynthesisResult(BaseModel):
    """The payload returned by the Modal TTS service (see ../../../tts/app.py)."""

    audio_base64: str
    format: str
    sample_rate: int
    duration: float
    paragraphs: list[Paragraph]
