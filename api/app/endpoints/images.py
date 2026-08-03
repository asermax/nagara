from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import get_db
from ..models.item import Item
from ..security import require_key
from ..service.storage import image_storage

# Shares the /items prefix and the key guard with the items router so invariant 4 holds
# uniformly: every route that touches an item requires the key, image serving included.
router = APIRouter(prefix="/items", tags=["items"], dependencies=[Depends(require_key)])


@router.get("/{item_id}/images/{image_hash}")
async def get_image(item_id: str, image_hash: str, db: AsyncSession = Depends(get_db)) -> Response:
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    # The image object is keyed by its content hash alone (deduped across items), so the store
    # serves it without an item-id lookup; a missing hash 404s inside the seam.
    return image_storage.image_response(image_hash)
