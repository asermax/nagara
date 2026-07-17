from pydantic import BaseModel

from .items import Paragraph


class SynthesisResult(BaseModel):
    """The payload returned by the Modal TTS service (see ../../../tts/app.py)."""

    audio_base64: str
    format: str
    sample_rate: int
    duration: float
    paragraphs: list[Paragraph]
