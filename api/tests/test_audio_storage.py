from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.service.storage import audio, base


def test_audio_ext_maps_ogg_and_falls_back_to_wav():
    assert audio.audio_ext("audio/ogg") == "ogg"
    assert audio.audio_ext("audio/wav") == "wav"


def test_factory_selects_local_when_unconfigured(monkeypatch):
    monkeypatch.setattr(audio, "settings", SimpleNamespace(s3_configured=False))
    assert isinstance(audio.build_audio_storage(), audio.LocalAudioStorage)


def test_factory_selects_bucket_when_configured(monkeypatch, bucket_settings):
    bucket_settings()
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: MagicMock())
    assert isinstance(audio.build_audio_storage(), audio.BucketAudioStorage)


def test_bucket_audio_response_redirects_to_presigned_url(monkeypatch, bucket_settings):
    bucket_settings()
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://nagara-audio.storage.railway.app/itm_x.ogg?sig=abc"
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: client)

    response = audio.BucketAudioStorage().audio_response("itm_x", "ogg", "audio/ogg")

    assert isinstance(response, RedirectResponse)
    assert response.status_code == 307
    assert response.headers["location"] == "https://nagara-audio.storage.railway.app/itm_x.ogg?sig=abc"
    client.generate_presigned_url.assert_called_once()


def test_bucket_store_puts_object(monkeypatch, bucket_settings):
    bucket_settings()
    client = MagicMock()
    monkeypatch.setattr(base.boto3, "client", lambda *a, **k: client)

    audio.BucketAudioStorage().store("itm_x", "ogg", b"OggS", "audio/ogg")

    client.put_object.assert_called_once_with(
        Bucket="nagara-audio", Key="itm_x.ogg", Body=b"OggS", ContentType="audio/ogg"
    )


def test_local_store_then_serve_round_trip():
    store = audio.LocalAudioStorage()
    store.store("itm_test", "ogg", b"OggS-bytes", "audio/ogg")

    response = store.audio_response("itm_test", "ogg", "audio/ogg")
    assert isinstance(response, FileResponse)
    assert response.media_type == "audio/ogg"


def test_local_missing_audio_raises_404():
    store = audio.LocalAudioStorage()
    with pytest.raises(HTTPException) as exc:
        store.audio_response("itm_absent", "ogg", "audio/ogg")
    assert exc.value.status_code == 404
