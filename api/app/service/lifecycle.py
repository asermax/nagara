from typing import cast

from sqlalchemy import CursorResult, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..helpers import now_iso
from ..models import SessionLocal
from ..models.item import Item, ItemStatus
from ..service.cost import record_describer_cost, record_firecrawl_cost
from ..service.describe import enrich_with_descriptions
from ..service.extract import ExtractionError
from ..service.fallback import FirecrawlUsage, extract_with_fallback
from ..service.images import enrich_with_images
from ..service.tts import spawn_synthesis


async def advance_queued_item(item_id: str) -> None:
    """Move a queued item through fetch, segment, enrich, and spawn to generating.

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
    resume path.
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

        firecrawl_usage: FirecrawlUsage | None = None

        def _capture_firecrawl_cost(usage: FirecrawlUsage) -> None:
            nonlocal firecrawl_usage
            firecrawl_usage = usage

        try:
            title, units, html = await extract_with_fallback(
                item.url, settings.firecrawl_api_key, _capture_firecrawl_cost
            )
        except ExtractionError as e:
            # A firecrawl scrape that billed before the extraction came up empty still spent
            # the credit, so record it even on the path that fails the item.
            await _record_firecrawl_cost_if_any(db, item_id, firecrawl_usage)
            await _write_if_queued(db, item_id, status=ItemStatus.FAILED, error=str(e))
            return

        await _record_firecrawl_cost_if_any(db, item_id, firecrawl_usage)

        describe_kinds: list[str] = []

        def _count_describe(kind: str) -> None:
            describe_kinds.append(kind)

        try:
            units, image_degradations, image_requests = await enrich_with_images(
                html, item.url, title, units, item_id
            )
            units, describe_degradations = await enrich_with_descriptions(
                units,
                title,
                image_requests=image_requests,
                api_key=settings.gemini_api_key,
                on_describe=_count_describe,
            )
            degradations = image_degradations + describe_degradations
        except Exception as e:
            await _write_if_queued(
                db, item_id, status=ItemStatus.FAILED, error=f"enrichment: {type(e).__name__}: {e}"
            )
            return

        # Meter the describer calls that landed, one row per call tagged by kind (code or
        # image). Committed on its own, like firecrawl: each call was billed regardless of
        # whether the item goes on to reach generating.
        if describe_kinds:
            for kind in describe_kinds:
                await record_describer_cost(db, item_id, kind)
            await db.commit()

        try:
            modal_call_id = await run_in_threadpool(
                spawn_synthesis, [unit.spoken for unit in units], item.voice
            )
        except Exception as e:
            await _write_if_queued(
                db, item_id, status=ItemStatus.FAILED, error=f"spawn: {type(e).__name__}: {e}"
            )
            return

        await _write_if_queued(
            db,
            item_id,
            status=ItemStatus.GENERATING,
            title=title,
            units=[unit.model_dump() for unit in units],
            degradations=degradations or None,
            enriched_at=now_iso(),
            modal_call_id=modal_call_id,
        )


async def _record_firecrawl_cost_if_any(
    db: AsyncSession, item_id: str, usage: FirecrawlUsage | None
) -> None:
    # Commit the metered fact on its own: the credit is spent regardless of whether the item
    # goes on to generate or fail, and it must not depend on a later conditional write that a
    # concurrent poll can cause to land zero rows.
    if usage is None:
        return
    await record_firecrawl_cost(db, item_id, usage)
    await db.commit()


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
