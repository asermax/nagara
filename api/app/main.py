from contextlib import asynccontextmanager

from fastapi import FastAPI

from .endpoints import api_router
from .models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Nagara API", lifespan=lifespan)
app.include_router(api_router)
