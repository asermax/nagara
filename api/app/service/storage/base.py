import boto3
from botocore.client import Config

from ...config import settings


class StorageBase:
    """Bucket machinery shared by the audio and image backends.

    Only the boto3 setup is shared. The two stores are separate interfaces because images
    differ from audio on every axis — many per item, keyed for cross-article dedup, served by
    a URL embedded in persisted markdown — so they are never collapsed into one media store.
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
