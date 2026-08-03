from abc import ABC, abstractmethod

from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response

from ...config import settings
from .base import StorageBase


def audio_ext(content_type: str) -> str:
    return "ogg" if content_type == "audio/ogg" else "wav"


class AudioStorage(StorageBase, ABC):
    """Where a ready item's single audio file lives, and how it is served back.

    Two implementations, selected once from configuration: local files for dev/tests, an
    S3-compatible bucket in production. The audio route is a thin caller — the local-vs-bucket
    difference lives entirely behind this seam.
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
        self._client = self._bucket_client()

    def store(self, item_id: str, ext: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            Bucket=settings.s3_bucket,
            Key=f"{item_id}.{ext}",
            Body=data,
            ContentType=content_type,
        )

    def audio_response(self, item_id: str, ext: str, content_type: str) -> Response:
        return RedirectResponse(self._presigned_get(self._client, f"{item_id}.{ext}"), status_code=307)


def build_audio_storage() -> AudioStorage:
    return BucketAudioStorage() if settings.s3_configured else LocalAudioStorage()
