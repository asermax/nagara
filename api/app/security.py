from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

from .config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_key(key: str | None = Security(_api_key_header)) -> None:
    if key != settings.api_key:
        raise HTTPException(status_code=401, detail="invalid or missing X-API-Key")
