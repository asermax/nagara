import base64
from datetime import datetime, timezone

from .models.item import Item
from .schemas.tts import SynthesisResult
from .service.storage import audio_ext, audio_storage


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def store_result(item: Item, result: SynthesisResult) -> None:
    audio_storage.store(
        item.id,
        audio_ext(result.format),
        base64.b64decode(result.audio_base64),
        result.format,
    )
    item.status = "ready"
    item.duration = result.duration
    item.audio_format = result.format
    item.paragraphs = [p.model_dump() for p in result.paragraphs]
