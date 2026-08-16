import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.cost import CostEntry
from .fallback import FirecrawlUsage


def _cost_id() -> str:
    return "cst_" + uuid.uuid4().hex[:12]


async def record_firecrawl_cost(db: AsyncSession, item_id: str, usage: FirecrawlUsage) -> None:
    """Stage a firecrawl cost row: the credits firecrawl reported, priced at write time.

    Adds to the session but does not commit — the credit is spent the moment firecrawl is
    called, so the caller commits it immediately rather than letting it ride the item's own
    conditional write, which may never land if a concurrent poll moves the item off queued.
    """
    db.add(
        CostEntry(
            id=_cost_id(),
            item_id=item_id,
            type="firecrawl",
            quantity=usage.credits,
            unit="credits",
            dollars=usage.credits * settings.firecrawl_dollars_per_credit,
            detail={"destination": usage.destination, "proxy": usage.proxy},
        )
    )


async def record_describer_cost(db: AsyncSession, item_id: str, kind: str) -> None:
    """Stage a describer cost row: one Gemini call, priced per call at write time.

    Adds without committing; the caller commits the batch on its own once enrichment resolves,
    for the same reason firecrawl does — the call is billed regardless of whether the item then
    reaches generating. `kind` is the describable's type (`code` or `image`), so the ledger can
    later separate image from code describer spend and tune the per-item cap on evidence.
    """
    db.add(
        CostEntry(
            id=_cost_id(),
            item_id=item_id,
            type="describer",
            quantity=1,
            unit="calls",
            dollars=settings.gemini_dollars_per_call,
            detail={"kind": kind},
        )
    )


async def record_tts_cost(db: AsyncSession, item_id: str, duration: float) -> None:
    """Stage a tts cost row: TTS bills on audio duration, priced at write time.

    Adds to the session without committing — it rides the same commit that finalizes the
    item to ready, so audio, timing, and cost land together.
    """
    db.add(
        CostEntry(
            id=_cost_id(),
            item_id=item_id,
            type="tts",
            quantity=duration,
            unit="seconds",
            dollars=duration * settings.tts_dollars_per_second,
            detail={"duration": duration},
        )
    )
