from abc import ABC, abstractmethod

import boto3
from botocore.client import Config
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from ..config import settings


def audio_ext(content_type: str) -> str:
    return "ogg" if content_type == "audio/ogg" else "wav"


class AudioStorage(ABC):
    """Where a ready item's audio lives, and how it is served back.

    Two implementations, selected once from configuration: local files for dev/tests,
    an S3-compatible bucket in production. The audio route is a thin caller — the
    local-vs-bucket difference lives entirely behind this seam.
    """

    @abstractmethod
    def store(self, item_id: str, ext: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def audio_response(self, item_id: str, ext: str, content_type: str) -> Response: ...


class LocalAudioStorage(AudioStorage):
    def store(self, item_id: str, ext: str, data: bytes, content_type: str) -> None:
        settings.audio_dir.mkdir(parents=True, exist_ok=True)
        (settings.audio_dir / f"{item_id}.{ext}").write_bytes(data)

    def audio_response(self, item_id: str, ext: str, content_type: str) -> Response:
        path = settings.audio_dir / f"{item_id}.{ext}"
        if not path.exists():
            raise HTTPException(404, "audio not available")
        return FileResponse(path, media_type=content_type)


class BucketAudioStorage(AudioStorage):
    def __init__(self) -> None:
        # Pin the addressing style so boto3 doesn't guess path-style against the custom endpoint.
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=Config(s3={"addressing_style": settings.s3_addressing_style}),
        )

    def store(self, item_id: str, ext: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=settings.s3_bucket,
            Key=f"{item_id}.{ext}",
            Body=data,
            ContentType=content_type,
        )

    def audio_response(self, item_id: str, ext: str, content_type: str) -> Response:
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": f"{item_id}.{ext}"},
            ExpiresIn=settings.s3_url_ttl,
        )
        return RedirectResponse(url, status_code=307)


def _build_storage() -> AudioStorage:
    return BucketAudioStorage() if settings.s3_configured else LocalAudioStorage()


audio_storage = _build_storage()
