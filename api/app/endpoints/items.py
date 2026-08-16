import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..helpers import now_iso, store_result
from ..models import get_db
from ..models.item import Item, ItemStatus
from ..schemas.items import CreateItemPayload, ItemResponse
from ..schemas.tts import SynthesisResult
from ..security import require_key
from ..service.lifecycle import advance_queued_item, claim_for_retry
from ..service.storage import audio_ext, audio_storage, image_storage
from ..service.tts import pick_voice, poll_synthesis

router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(require_key)])


def _apply_queued_ceiling(item: Item) -> None:
    # A queued item whose task died with the container is failed on the next poll once its
    # work age passes the ceiling. queued_at is set in the enqueue write, so a row stranded
    # before its task ever ran still has a clock; the None branch is defensive only.
    if item.status != ItemStatus.QUEUED or item.queued_at is None:
        return
    age = datetime.now(timezone.utc) - datetime.fromisoformat(item.queued_at)
    if age.total_seconds() > settings.queued_ceiling_seconds:
        item.status = ItemStatus.FAILED
        item.error = f"enrichment: no result after {settings.queued_ceiling_seconds}s"


@router.post("", status_code=202, response_model=ItemResponse)
async def create_item(
    body: CreateItemPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Item:
    item = Item(
        id="itm_" + uuid.uuid4().hex[:8],
        url=body.url,
        status=ItemStatus.QUEUED,
        voice=body.voice or pick_voice(),
        created_at=now_iso(),
        queued_at=now_iso(),
    )
    db.add(item)
    # Commit before scheduling the task: the task opens its own session, so the row must
    # be persisted for it to read. The response is serialized from this queued item
    # before the task runs, so a client sees queued on the POST and generating on the poll.
    await db.commit()
    background_tasks.add_task(advance_queued_item, item.id)
    return item


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)) -> Item:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")

    _apply_queued_ceiling(item)

    if item.status == ItemStatus.GENERATING and item.modal_call_id:
        status, payload = await run_in_threadpool(poll_synthesis, item.modal_call_id)
        if status == ItemStatus.READY and isinstance(payload, SynthesisResult):
            try:
                await store_result(item, payload, db)
            except Exception as e:
                item.status = ItemStatus.FAILED
                item.error = f"store: {type(e).__name__}: {e}"
        elif status == ItemStatus.FAILED:
            item.status = ItemStatus.FAILED
            item.error = f"tts: {payload}"

    return item


@router.get("/{item_id}/audio")
async def get_audio(item_id: str, db: AsyncSession = Depends(get_db)) -> Response:
    item = await db.get(Item, item_id)
    if item is None or item.status != ItemStatus.READY or item.audio_format is None:
        raise HTTPException(404, "audio not available")
    return audio_storage.audio_response(item.id, audio_ext(item.audio_format), item.audio_format)


@router.get("/{item_id}/images/{image_hash}")
async def get_image(item_id: str, image_hash: str, db: AsyncSession = Depends(get_db)) -> Response:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    # The image object is keyed by its content hash alone (deduped across items), so the store
    # serves it without an item-id lookup; a missing hash 404s inside the seam.
    return image_storage.image_response(image_hash)


@router.post("/{item_id}/retry", status_code=202, response_model=ItemResponse)
async def retry_item(
    item_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Item:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")

    # The transition is a single conditional UPDATE decided by the write, not a read-then-
    # write: two concurrent retries on one item cannot both pass, because only the first finds
    # status still failed and under the cap. A rowcount of 0 is the 409; the pre-read only
    # picks the message, refreshing the row so a concurrent retry that won the race reports
    # its new status rather than the stale failed one.
    if not await claim_for_retry(db, item_id):
        await db.refresh(item)
        if item.status != ItemStatus.FAILED:
            raise HTTPException(409, f"item is {item.status.value}, not failed")
        raise HTTPException(409, f"retry limit reached ({settings.retry_max})")

    await db.refresh(item)
    background_tasks.add_task(advance_queued_item, item.id)
    return item
