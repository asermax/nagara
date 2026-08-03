from fastapi import APIRouter

from .images import router as images_router
from .items import router as items_router

api_router = APIRouter()
api_router.include_router(items_router)
api_router.include_router(images_router)
