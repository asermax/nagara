import hashlib
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse, Response
from PIL import Image, UnidentifiedImageError

from ..config import settings

# Accepted source formats, validated by decoding rather than trusting Content-Type (wrong or
# missing on most image CDNs). The describer's set.
_ACCEPTED_IMAGE_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}


def audio_ext(content_type: str) -> str:
    return "ogg" if content_type == "audio/ogg" else "wav"


class _StorageBase:
    """Storage machinery shared by the audio and image backends.

    AudioStorage and ImageStorage inherit this base as two separate interfaces: images differ
    from audio on every axis (many per item, keyed for cross-article dedup, served by a URL
    embedded in persisted markdown), so they are not collapsed into one media store. Factoring
    the bucket-client construction into the base avoids copy-pasting the boto3 setup.
    """

    @staticmethod
    def _bucket_client():
        # Pin the addressing style so boto3 doesn't guess path-style against the custom endpoint.
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=Config(s3={"addressing_style": settings.s3_addressing_style}),
        )

    @staticmethod
    def _presigned_get(client, key: str) -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=settings.s3_url_ttl,
        )


class AudioStorage(_StorageBase, ABC):
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


def _encode_image(data: bytes) -> tuple[str, bytes]:
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


class ImageStorage(_StorageBase, ABC):
    """Where an item's images live, keyed by a content hash of the re-encoded WebP bytes,
    and how they are served back.

    Many per item, deduped across items and across re-enqueues by the content hash (not the
    item id, not the origin URL). Served by a URL embedded in persisted markdown, so the
    response is minted fresh at read time — a presigned URL written into the row would be dead
    inside s3_url_ttl, and the unit list is persisted indefinitely.
    """

    def store(self, data: bytes) -> str:
        image_hash, webp = _encode_image(data)
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


def _build_storage() -> AudioStorage:
    return BucketAudioStorage() if settings.s3_configured else LocalAudioStorage()


def _build_image_storage() -> ImageStorage:
    return BucketImageStorage() if settings.s3_configured else LocalImageStorage()


audio_storage = _build_storage()
image_storage = _build_image_storage()
