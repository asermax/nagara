import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ..helpers import now_iso, store_result
from ..models import get_db
from ..models.item import Item, ItemStatus
from ..schemas.items import CreateItemPayload, ItemResponse
from ..schemas.tts import SynthesisResult
from ..security import require_key
from ..service.extract import ExtractionError, extract_article
from ..service.storage import audio_ext, audio_storage
from ..service.tts import pick_voice, poll_synthesis, spawn_synthesis

router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(require_key)])


@router.post("", status_code=202, response_model=ItemResponse)
async def create_item(body: CreateItemPayload, db: AsyncSession = Depends(get_db)) -> Item:
    item = Item(
        id="itm_" + uuid.uuid4().hex[:8],
        url=body.url,
        status=ItemStatus.GENERATING,
        voice=body.voice or pick_voice(),
        created_at=now_iso(),
    )
    db.add(item)

    # trafilatura (network fetch + CPU-bound extract) and the Modal client are synchronous and
    # blocking, so each call is bridged off the event loop.
    try:
        item.title, units = await run_in_threadpool(extract_article, body.url)
    except ExtractionError as e:
        item.status = ItemStatus.FAILED
        item.error = f"extraction: {e}"
        return item

    item.units = [unit.model_dump() for unit in units]

    try:
        item.modal_call_id = await run_in_threadpool(
            spawn_synthesis, [unit.spoken for unit in units], item.voice
        )
    except Exception as e:
        item.status = ItemStatus.FAILED
        item.error = f"spawn: {type(e).__name__}: {e}"

    return item


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)) -> Item:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")

    if item.status == ItemStatus.GENERATING and item.modal_call_id:
        status, payload = await run_in_threadpool(poll_synthesis, item.modal_call_id)
        if status == ItemStatus.READY and isinstance(payload, SynthesisResult):
            try:
                await store_result(item, payload)
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
