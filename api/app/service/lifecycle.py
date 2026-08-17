from typing import cast

from sqlalchemy import CursorResult, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..helpers import now_iso
from ..models import SessionLocal
from ..models.item import Item, ItemStatus
from .pipeline import pipeline


async def advance_queued_item(item_id: str) -> None:
    """Drive a queued item through the pipeline's queued phase to generating.

    Runs as a BackgroundTasks handler inside the API process, which makes it mortal: a redeploy
    kills it mid-flight, and the queued_at ceiling plus the retry route recover from that. It
    opens its own session and hands the item to ``pipeline.advance``, which runs the queued
    steps (source, image, describe, spawn) with each write guarded on the item still being
    queued, and resumes from whichever step the item's state wants — straight to spawn when a
    previous run already enriched it.
    """
    async with SessionLocal() as db:
        item = await db.get(Item, item_id)
        if item is None or item.status != ItemStatus.QUEUED:
            return
        await pipeline.advance(item, db)


async def claim_for_retry(db: AsyncSession, item_id: str) -> bool:
    """Atomically move a failed item back to queued for a retry.

    A single conditional UPDATE is the arbiter, not a read-then-write: it gates on status
    still failed AND retry_count below the cap, and increments retry_count in SQL. So two
    concurrent retries on one item cannot both win — only the first UPDATE finds the
    preconditions still met, the second gets rowcount 0 and the route refuses it. This is
    the same problem the pipeline's guarded write solves for the queued→generating transition;
    mirroring its shape keeps the read-then-write race out of the retry path too, which matters
    because a manual recovery route is exactly where a double-click is plausible. retry_count is
    nullable until the first retry, so the guard and the increment both coalesce NULL to 0.
    """
    result = cast(
        CursorResult,
        await db.execute(
            update(Item)
            .where(
                Item.id == item_id,
                Item.status == ItemStatus.FAILED,
                or_(Item.retry_count.is_(None), Item.retry_count < settings.retry_max),
            )
            .values(
                status=ItemStatus.QUEUED,
                queued_at=now_iso(),
                error=None,
                retry_count=func.coalesce(Item.retry_count, 0) + 1,
            )
        ),
    )
    if result.rowcount == 0:
        return False
    await db.commit()
    return True
