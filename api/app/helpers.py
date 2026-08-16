import base64
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .models.item import Item, ItemStatus
from .schemas.tts import SynthesisResult
from .service.cost import record_tts_cost
from .service.storage import audio_ext, audio_storage


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def store_result(item: Item, result: SynthesisResult, db: AsyncSession) -> None:
    units = item.units or []
    if len(units) != len(result.paragraphs):
        raise ValueError(
            f"alignment mismatch: {len(units)} units vs {len(result.paragraphs)} timed"
        )

    # boto3's S3 client (and the local file write behind the same seam) is synchronous and
    # blocking, so it runs off the event loop.
    await run_in_threadpool(
        audio_storage.store,
        item.id,
        audio_ext(result.format),
        base64.b64decode(result.audio_base64),
        result.format,
    )
    item.status = ItemStatus.READY
    item.duration = result.duration
    item.audio_format = result.format
    # The timeline is position-keyed: the spoken text was synthesized, and each window is
    # joined back onto its unit by index. Invariant 2 holds by construction — one source
    # list, no text matching — and the length guard above fails the item on a mismatch.
    item.units = [
        {**units[p.index], "index": p.index, "start": p.start, "end": p.end}
        for p in result.paragraphs
    ]

    # TTS bills on duration; record it in the same session so the cost commits with the
    # ready transition.
    await record_tts_cost(db, item.id, result.duration)
