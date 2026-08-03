from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from PIL import Image

from app.service import storage

FIXTURES = Path(__file__).parent / "fixtures"


def _bucket_settings():
    return SimpleNamespace(
        s3_configured=True,
        s3_endpoint="https://storage.railway.app",
        s3_bucket="nagara-audio",
        s3_access_key_id="k",
        s3_secret_access_key="s",
        s3_region="auto",
        s3_addressing_style="virtual",
        s3_url_ttl=3600,
    )


def test_audio_ext_maps_ogg_and_falls_back_to_wav():
    assert storage.audio_ext("audio/ogg") == "ogg"
    assert storage.audio_ext("audio/wav") == "wav"


def test_factory_selects_local_when_unconfigured(monkeypatch):
    monkeypatch.setattr(storage, "settings", SimpleNamespace(s3_configured=False))
    assert isinstance(storage._build_storage(), storage.LocalAudioStorage)


def test_factory_selects_bucket_when_configured(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: MagicMock())
    assert isinstance(storage._build_storage(), storage.BucketAudioStorage)


def test_bucket_audio_response_redirects_to_presigned_url(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://nagara-audio.storage.railway.app/itm_x.ogg?sig=abc"
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)

    response = storage.BucketAudioStorage().audio_response("itm_x", "ogg", "audio/ogg")

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://nagara-audio.storage.railway.app/itm_x.ogg?sig=abc"
    client.generate_presigned_url.assert_called_once()


def test_bucket_store_puts_object(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    client = MagicMock()
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)

    storage.BucketAudioStorage().store("itm_x", "ogg", b"OggS", "audio/ogg")

    client.put_object.assert_called_once_with(
        Bucket="nagara-audio", Key="itm_x.ogg", Body=b"OggS", ContentType="audio/ogg"
    )


def test_local_store_then_serve_round_trip():
    store = storage.LocalAudioStorage()
    store.store("itm_test", "ogg", b"OggS-bytes", "audio/ogg")

    response = store.audio_response("itm_test", "ogg", "audio/ogg")
    assert isinstance(response, FileResponse)
    assert response.media_type == "audio/ogg"


def test_local_missing_audio_raises_404():
    store = storage.LocalAudioStorage()
    with pytest.raises(HTTPException) as exc:
        store.audio_response("itm_absent", "ogg", "audio/ogg")
    assert exc.value.status_code == 404


# --- ImageStorage: decode, re-encode to WebP, content-hash key, dedup, serve ---


def test_image_factory_selects_local_when_unconfigured(monkeypatch):
    monkeypatch.setattr(storage, "settings", SimpleNamespace(s3_configured=False))
    assert isinstance(storage._build_image_storage(), storage.LocalImageStorage)


def test_image_factory_selects_bucket_when_configured(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: MagicMock())
    assert isinstance(storage._build_image_storage(), storage.BucketImageStorage)


def test_image_store_round_trip_local(monkeypatch, tmp_path):
    # the assertion worth making hardest: a real image through decode, re-encode, hash, store, serve
    monkeypatch.setattr(storage, "settings", SimpleNamespace(image_dir=tmp_path))
    store = storage.LocalImageStorage()
    image_hash = store.store((FIXTURES / "sample.png").read_bytes())

    assert len(image_hash) == 64  # sha256 hex
    response = store.image_response(image_hash)
    assert isinstance(response, FileResponse)
    assert response.media_type == "image/webp"
    assert Image.open(BytesIO(Path(response.path).read_bytes())).format == "WEBP"


def test_image_store_dedups_same_bytes(monkeypatch, tmp_path):
    # the same image a second time must hit the stored object rather than re-storing
    monkeypatch.setattr(storage, "settings", SimpleNamespace(image_dir=tmp_path))
    store = storage.LocalImageStorage()
    put = MagicMock(wraps=store._put)
    store._put = put

    png = (FIXTURES / "sample.png").read_bytes()
    first = store.store(png)
    second = store.store(png)

    assert first == second
    assert put.call_count == 1


def test_image_store_rejects_undecodable():
    with pytest.raises(ValueError):
        storage._encode_image(b"not an image at all")


def test_image_store_rejects_unsupported_format():
    # decodes fine but is not one of the accepted formats
    buf = BytesIO()
    Image.new("RGB", (8, 8)).save(buf, "BMP")
    with pytest.raises(ValueError, match="unsupported"):
        storage._encode_image(buf.getvalue())


def test_image_local_missing_raises_404(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "settings", SimpleNamespace(image_dir=tmp_path))
    with pytest.raises(HTTPException) as exc:
        storage.LocalImageStorage().image_response("nope")
    assert exc.value.status_code == 404


def test_bucket_image_store_puts_object(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    client = MagicMock()
    client.head_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)

    image_hash = storage.BucketImageStorage().store((FIXTURES / "sample.png").read_bytes())

    client.put_object.assert_called_once()
    assert client.put_object.call_args.kwargs["Key"] == f"images/{image_hash}.webp"
    assert client.put_object.call_args.kwargs["ContentType"] == "image/webp"


def test_bucket_image_store_skips_put_when_exists(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    client = MagicMock()  # head_object returns without raising -> object exists
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)

    image_hash = storage.BucketImageStorage().store((FIXTURES / "sample.png").read_bytes())

    client.head_object.assert_called_once()
    client.put_object.assert_not_called()
    assert len(image_hash) == 64


def test_bucket_image_response_redirects_to_presigned_url(monkeypatch):
    monkeypatch.setattr(storage, "settings", _bucket_settings())
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://signed.example/images/abc.webp"
    monkeypatch.setattr(storage.boto3, "client", lambda *a, **k: client)

    response = storage.BucketImageStorage().image_response("abc123")

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://signed.example/images/abc.webp"
    client.generate_presigned_url.assert_called_once()
