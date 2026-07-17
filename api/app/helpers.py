import base64
from datetime import datetime, timezone

from .config import settings
from .models.item import Item
from .schemas.tts import SynthesisResult


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def store_result(item: Item, result: SynthesisResult) -> None:
    """Persist a ready synthesis onto the item: write the audio file, set the fields."""
    ext = "ogg" if result.format == "audio/ogg" else "wav"
    (settings.audio_dir / f"{item.id}.{ext}").write_bytes(base64.b64decode(result.audio_base64))
    item.status = "ready"
    item.duration = result.duration
    item.audio_format = result.format
    item.paragraphs = [p.model_dump() for p in result.paragraphs]
