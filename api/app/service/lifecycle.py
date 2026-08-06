from typing import cast

from sqlalchemy import CursorResult, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..helpers import now_iso
from ..models import SessionLocal
from ..models.item import Item, ItemStatus
from ..service.extract import ExtractionError, extract_article
from ..service.tts import spawn_synthesis


async def advance_queued_item(item_id: str) -> None:
    """Move a queued item through fetch, segment, and spawn to generating.

    Runs as a BackgroundTasks handler inside the API process, which makes it mortal: a
    redeploy kills it mid-flight, and the queued_at ceiling plus the retry route recover
    from that. Every write is conditional on the item still being queued, so a poll that
    fails the item at the ceiling while this task runs cannot be overwritten — the task
    abandons its work and commits nothing further. Nothing is lost: the only thing the
    task would have written past the failure is the generating transition, and a retry
    resumes from any units already on the row.

    When enriched_at is already set (a previous run reached generating and failed
    downstream at poll or store), the task re-spawns synthesis straight from the units on
    the row and skips fetch and segment entirely: that is the retry route's zero-cost
    resume path. Otherwise, enrichment is not built yet, so this fetches and segments and
    sets enriched_at in the same write as the spawn. Later quests plug enrichment steps
    into the gap between segment and spawn without rebuilding the path.
    """
    async with SessionLocal() as db:
        item = await db.get(Item, item_id)
        if item is None or item.status != ItemStatus.QUEUED:
            return

        if item.enriched_at and item.units:
            # Resume path: a previous run reached generating (enrichment complete) and
            # failed downstream at poll or store. Re-spawn only — no fetch, no segment —
            # so a crash on someone else's GPU costs nothing to recover from. The spoken
            # text is already on the row, so there is nothing to re-describe either.
            try:
                modal_call_id = await run_in_threadpool(
                    spawn_synthesis, [unit["spoken"] for unit in item.units], item.voice
                )
            except Exception as e:
                await _write_if_queued(
                    db, item_id, status=ItemStatus.FAILED, error=f"spawn: {type(e).__name__}: {e}"
                )
                return
            await _write_if_queued(
                db, item_id, status=ItemStatus.GENERATING, modal_call_id=modal_call_id
            )
            return

        # queued_at is the ceiling's clock and is set in the enqueue write, so a stranded
        # row (container died before this task ran) still has one. Every write below is
        # conditional on the item still being queued, which is what keeps a late task from
        # resurrecting a row poll already failed at the ceiling.
        try:
            title, units = await run_in_threadpool(extract_article, item.url)
        except ExtractionError as e:
            await _write_if_queued(db, item_id, status=ItemStatus.FAILED, error=f"extraction: {e}")
            return

        try:
            modal_call_id = await run_in_threadpool(
                spawn_synthesis, [unit.spoken for unit in units], item.voice
            )
        except Exception as e:
            await _write_if_queued(
                db, item_id, status=ItemStatus.FAILED, error=f"spawn: {type(e).__name__}: {e}"
            )
            return

        # The generating transition carries the handle and the status together, so the
        # unreachable "generating with no modal_call_id" state can never be observed.
        await _write_if_queued(
            db,
            item_id,
            status=ItemStatus.GENERATING,
            title=title,
            units=[unit.model_dump() for unit in units],
            enriched_at=now_iso(),
            modal_call_id=modal_call_id,
        )


async def _write_if_queued(db: AsyncSession, item_id: str, **values) -> bool:
    """Apply an UPDATE only while the item is still queued, returning whether it landed.

    A rowcount of zero means a concurrent poll already moved the item off queued (the
    ceiling fails it); the caller treats that as abandon-and-commit-nothing. SQLite reports
    changed rows rather than matched rows, which is reliable here because every write moves
    at least one column off its previous value.
    """
    result = cast(
        CursorResult,
        await db.execute(
            update(Item)
            .where(Item.id == item_id, Item.status == ItemStatus.QUEUED)
            .values(**values)
        ),
    )
    if result.rowcount == 0:
        return False
    await db.commit()
    return True


async def claim_for_retry(db: AsyncSession, item_id: str) -> bool:
    """Atomically move a failed item back to queued for a retry.

    A single conditional UPDATE is the arbiter, not a read-then-write: it gates on status
    still failed AND retry_count below the cap, and increments retry_count in SQL. So two
    concurrent retries on one item cannot both win — only the first UPDATE finds the
    preconditions still met, the second gets rowcount 0 and the route refuses it. This is
    the same problem _write_if_queued solves for the queued→generating transition; mirroring
    its shape keeps the read-then-write race out of the retry path too, which matters because
    a manual recovery route is exactly where a double-click is plausible. retry_count is
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
