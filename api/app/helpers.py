import base64
from datetime import datetime, timezone

from .models.item import Item
from .schemas.tts import SynthesisResult
from .service.storage import audio_ext, audio_storage


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def store_result(item: Item, result: SynthesisResult) -> None:
    display = item.display or []
    if len(display) != len(result.paragraphs):
        raise ValueError(
            f"alignment mismatch: {len(display)} display units vs {len(result.paragraphs)} timed"
        )

    audio_storage.store(
        item.id,
        audio_ext(result.format),
        base64.b64decode(result.audio_base64),
        result.format,
    )
    item.status = "ready"
    item.duration = result.duration
    item.audio_format = result.format
    # The spoken text was synthesized; the timeline is position-keyed, so joining the
    # display markdown back on by index is what surfaces formatting to the client.
    item.paragraphs = [
        {"index": p.index, "start": p.start, "end": p.end, "text": display[p.index]}
        for p in result.paragraphs
    ]
