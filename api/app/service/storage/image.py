import hashlib
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from PIL import Image, UnidentifiedImageError

from ...config import settings
from .base import StorageBase

# Accepted source formats, validated by decoding rather than trusting Content-Type (wrong or
# missing on most image CDNs). The describer's set.
_ACCEPTED_IMAGE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}


def encode_image(data: bytes) -> tuple[str, bytes]:
    """Decode-validate with Pillow, re-encode to WebP, return (content_hash, webp_bytes).

    Format is verified by decoding, never by trusting Content-Type. Re-encoding before hashing
    dedupes across source-format variants of the same image. Animated GIFs collapse to the
    static first frame. A file that will not decode, or is not one of the accepted formats,
    raises ValueError — the caller drops the unit.
    """
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format not in _ACCEPTED_IMAGE_FORMATS:
                raise ValueError(f"unsupported image format: {image.format}")
            image.load()
            buffer = BytesIO()
            image.save(buffer, format="WEBP")
    except UnidentifiedImageError as e:
        raise ValueError(f"undecodable image: {e}") from e

    webp = buffer.getvalue()
    return hashlib.sha256(webp).hexdigest(), webp


class ImageStorage(StorageBase, ABC):
    """Where an item's images live, keyed by a content hash of the re-encoded WebP bytes,
    and how they are served back.

    Many per item, deduped across items and across re-enqueues by the content hash (not the
    item id, not the origin URL). Served by a URL embedded in persisted markdown, so the
    response is minted fresh at read time — a presigned URL written into the row would be dead
    inside s3_url_ttl, and the unit list is persisted indefinitely.
    """

    def store(self, data: bytes) -> str:
        image_hash, webp = encode_image(data)
        if not self._exists(image_hash):
            self._put(image_hash, webp)
        return image_hash

    @abstractmethod
    def _exists(self, image_hash: str) -> bool: ...

    @abstractmethod
    def _put(self, image_hash: str, data: bytes) -> None: ...

    @abstractmethod
    def image_response(self, image_hash: str) -> Response: ...


class LocalImageStorage(ImageStorage):
    def _path(self, image_hash: str) -> Path:
        return settings.image_dir / f"{image_hash}.webp"

    def _exists(self, image_hash: str) -> bool:
        return self._path(image_hash).exists()

    def _put(self, image_hash: str, data: bytes) -> None:
        settings.image_dir.mkdir(parents=True, exist_ok=True)
        self._path(image_hash).write_bytes(data)

    def image_response(self, image_hash: str) -> Response:
        path = self._path(image_hash)
        if not path.exists():
            raise HTTPException(404, "image not available")
        return FileResponse(path, media_type="image/webp")


class BucketImageStorage(ImageStorage):
    def __init__(self) -> None:
        self._client = self._bucket_client()

    @staticmethod
    def _key(image_hash: str) -> str:
        return f"images/{image_hash}.webp"

    def _exists(self, image_hash: str) -> bool:
        try:
            self._client.head_object(Bucket=settings.s3_bucket, Key=self._key(image_hash))
            return True
        except ClientError:
            return False

    def _put(self, image_hash: str, data: bytes) -> None:
        self._client.put_object(
            Bucket=settings.s3_bucket,
            Key=self._key(image_hash),
            Body=data,
            ContentType="image/webp",
        )

    def image_response(self, image_hash: str) -> Response:
        return RedirectResponse(self._presigned_get(self._client, self._key(image_hash)), status_code=307)


def build_image_storage() -> ImageStorage:
    return BucketImageStorage() if settings.s3_configured else LocalImageStorage()
