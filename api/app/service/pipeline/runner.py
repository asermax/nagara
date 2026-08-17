from typing import Protocol, cast

from pydantic import TypeAdapter
from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.item import Item, ItemStatus
from ...schemas.items import Unit
from ..extract import ExtractionError
from .context import PipelineContext

_UNIT_LIST = TypeAdapter(list[Unit])


class PipelineStep(Protocol):
    """One phase of the pipeline. ``phase`` is the item status this step advances from — the
    runner only offers it items in that status, so the same status that names the state also
    names who drives the step: a ``queued`` step runs in the mortal background task, a
    ``generating`` step on a client poll. ``name`` is the ``error:`` prefix it owns. ``wants``
    is the precondition over the working context, so resume is just which step wants the item.
    """

    name: str
    phase: ItemStatus

    def wants(self, ctx: PipelineContext) -> bool: ...

    async def run(self, ctx: PipelineContext, db: AsyncSession) -> None: ...


class Pipeline:
    """One ordered list of steps, positioned by item state. ``advance`` is the single entry for
    enqueue, retry, and poll: it runs the steps of the item's current status in order, each one
    gated by its own ``wants``, persisting per step. It stops when the phase flips (a step moved
    the item off its starting status), a step fails, a write is abandoned, or nothing wants more.
    """

    def __init__(self, steps: list[PipelineStep]):
        self.steps = steps

    async def advance(self, item: Item, db: AsyncSession) -> Item:
        if item.status not in (ItemStatus.QUEUED, ItemStatus.GENERATING):
            return item

        phase = item.status
        ctx = self._seed(item)

        for step in self.steps:
            if step.phase != phase or not step.wants(ctx):
                continue

            ctx.write = {}
            try:
                await step.run(ctx, db)
            except Exception as e:
                await self._fail(db, item, phase, step, e)
                return item

            if not ctx.write:
                continue

            if not await self._persist(db, item, phase, ctx):
                # A concurrent poll already moved the item off queued (the ceiling failed it):
                # the guarded write matched zero rows, so abandon and commit nothing further.
                return item

            if ctx.write.get("status", phase) != phase:
                # The phase flipped (queued → generating) or the step failed the item: the next
                # step belongs to a different driver, so this call is done.
                return item

        return item

    async def _persist(self, db: AsyncSession, item: Item, phase: ItemStatus, ctx: PipelineContext) -> bool:
        if phase == ItemStatus.QUEUED:
            # Guarded raw UPDATE, never an ORM mutation: the object stays pristine so a later
            # autoflush cannot slip an unguarded write past the WHERE status = 'queued' clause.
            return await self._write_if_queued(db, ctx.item_id, **ctx.write)

        # Generating runs inside the poll request and is the item's only writer, so it mutates
        # the ORM object and rides the request's own commit (get_db).
        for key, value in ctx.write.items():
            setattr(item, key, value)
        return True

    async def _fail(self, db: AsyncSession, item: Item, phase: ItemStatus, step: PipelineStep, e: Exception) -> None:
        # An ExtractionError already carries its own phase prefix (fetch: / extraction:); every
        # other exception is named by the step that raised it.
        error = str(e) if isinstance(e, ExtractionError) else f"{step.name}: {type(e).__name__}: {e}"
        if phase == ItemStatus.QUEUED:
            await self._write_if_queued(db, item.id, status=ItemStatus.FAILED, error=error)
        else:
            item.status = ItemStatus.FAILED
            item.error = error

    @staticmethod
    def _seed(item: Item) -> PipelineContext:
        # The context copies the row's fields rather than wrapping the item and reading through
        # it: a step's working state (title, units, enriched_at) runs ahead of the persisted row
        # until its write lands, and reading those through the item would mean writing through it
        # too — dirtying the ORM object so a later autoflush slips an unguarded UPDATE past the
        # queued guard (see _persist). Keeping the context pure data is what keeps the item
        # pristine and the mortality guard sound.
        return PipelineContext(
            item_id=item.id,
            url=item.url,
            voice=item.voice,
            phase=item.status,
            title=item.title,
            units=_UNIT_LIST.validate_python(item.units) if item.units else [],
            enriched_at=item.enriched_at,
            modal_call_id=item.modal_call_id,
        )

    @staticmethod
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
