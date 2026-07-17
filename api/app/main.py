from fastapi import FastAPI

from .endpoints import api_router

app = FastAPI(title="Nagara API")
app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
