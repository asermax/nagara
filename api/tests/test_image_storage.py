from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from PIL import Image

from app.service.storage import base, image

FIXTURES = Path(__file__).parent / "fixtures"


def test_factory_selects_local_when_unconfigured(monkeypatch):
    monkeypatch.setattr(image, "settings", SimpleNamespace(s3_configured=False))
    assert isinstance(image.build_image_storage(), image.LocalImageStorage)


def test_factory_selects_bucket_when_configured(monkeypatch, bucket_settings):
    bucket_settings()
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: MagicMock())
    assert isinstance(image.build_image_storage(), image.BucketImageStorage)


def test_store_round_trip_local(monkeypatch, tmp_path):
    # the assertion worth making hardest: a real image through decode, re-encode, hash, store, serve
    monkeypatch.setattr(image, "settings", SimpleNamespace(image_dir=tmp_path))
    store = image.LocalImageStorage()
    image_hash = store.store((FIXTURES / "sample.png").read_bytes())

    assert len(image_hash) == 64  # sha256 hex
    response = store.image_response(image_hash)
    assert isinstance(response, FileResponse)
    assert response.media_type == "image/webp"
    assert Image.open(BytesIO(Path(response.path).read_bytes())).format == "WEBP"


def test_store_dedups_same_bytes(monkeypatch, tmp_path):
    # the same image a second time must hit the stored object rather than re-storing
    monkeypatch.setattr(image, "settings", SimpleNamespace(image_dir=tmp_path))
    store = image.LocalImageStorage()
    put = MagicMock(wraps=store._put)
    store._put = put

    png = (FIXTURES / "sample.png").read_bytes()
    first = store.store(png)
    second = store.store(png)

    assert first == second
    assert put.call_count == 1


def test_store_rejects_undecodable():
    with pytest.raises(ValueError):
        image.encode_image(b"not an image at all")


def test_store_rejects_unsupported_format():
    # decodes fine but is not one of the accepted formats
    buf = BytesIO()
    Image.new("RGB", (8, 8)).save(buf, "BMP")
    with pytest.raises(ValueError, match="unsupported"):
        image.encode_image(buf.getvalue())


def test_local_missing_raises_404(monkeypatch, tmp_path):
    monkeypatch.setattr(image, "settings", SimpleNamespace(image_dir=tmp_path))
    with pytest.raises(HTTPException) as exc:
        image.LocalImageStorage().image_response("nope")
    assert exc.value.status_code == 404


def test_bucket_store_puts_object(monkeypatch, bucket_settings):
    bucket_settings()
    client = MagicMock()
    client.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: client)

    image_hash = image.BucketImageStorage().store((FIXTURES / "sample.png").read_bytes())

    client.put_object.assert_called_once()
    assert client.put_object.call_args.kwargs["Key"] == f"images/{image_hash}.webp"
    assert client.put_object.call_args.kwargs["ContentType"] == "image/webp"


def test_bucket_store_skips_put_when_exists(monkeypatch, bucket_settings):
    bucket_settings()
    client = MagicMock()  # head_object returns without raising -> object exists
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: client)

    image_hash = image.BucketImageStorage().store((FIXTURES / "sample.png").read_bytes())

    client.head_object.assert_called_once()
    client.put_object.assert_not_called()
    assert len(image_hash) == 64


def test_bucket_response_redirects_to_presigned_url(monkeypatch, bucket_settings):
    bucket_settings()
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://signed.example/images/abc.webp"
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: client)

    response = image.BucketImageStorage().image_response("abc123")

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://signed.example/images/abc.webp"
    client.generate_presigned_url.assert_called_once()
