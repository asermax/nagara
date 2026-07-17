import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import settings
from ..helpers import now_iso, store_result
from ..models import get_db
from ..models.item import Item
from ..schemas.items import CreateItemPayload, ItemResponse
from ..schemas.tts import SynthesisResult
from ..security import require_key
from ..service.extract import ExtractionError, extract_article
from ..service.storage import audio_ext, audio_storage
from ..service.tts import poll_synthesis, spawn_synthesis

router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(require_key)])


@router.post("", status_code=202, response_model=ItemResponse)
def create_item(body: CreateItemPayload, db: Session = Depends(get_db)) -> Item:
    item = Item(
        id="itm_" + uuid.uuid4().hex[:8],
        url=body.url,
        status="generating",
        voice=body.voice or settings.default_voice,
        created_at=now_iso(),
    )
    db.add(item)

    try:
        item.title, paragraphs = extract_article(body.url)
    except ExtractionError as e:
        item.status = "failed"
        item.error = f"extraction: {e}"
        return item

    try:
        item.modal_call_id = spawn_synthesis(paragraphs, item.voice)
    except Exception as e:
        item.status = "failed"
        item.error = f"spawn: {type(e).__name__}: {e}"

    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: str, db: Session = Depends(get_db)) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")

    if item.status == "generating" and item.modal_call_id:
        status, payload = poll_synthesis(item.modal_call_id)
        if status == "ready" and isinstance(payload, SynthesisResult):
            try:
                store_result(item, payload)
            except Exception as e:
                item.status = "failed"
                item.error = f"store: {type(e).__name__}: {e}"
        elif status == "failed":
            item.status = "failed"
            item.error = f"tts: {payload}"

    return item


@router.get("/{item_id}/audio")
def get_audio(item_id: str, db: Session = Depends(get_db)) -> Response:
    item = db.get(Item, item_id)
    if item is None or item.status != "ready" or item.audio_format is None:
        raise HTTPException(404, "audio not available")
    return audio_storage.audio_response(item.id, audio_ext(item.audio_format), item.audio_format)
