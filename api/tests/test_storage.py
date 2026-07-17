from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.service import storage


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
