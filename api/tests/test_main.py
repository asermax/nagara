import base64
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.tts import SynthesisResult
from app.service.extract import ExtractionError

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}


def _create(url="https://example.test/post"):
    with (
        patch(
            "app.endpoints.items.extract_article",
            return_value=("Title", ["**p1**", "p2"], ["p1", "p2"]),
        ),
        patch("app.endpoints.items.spawn_synthesis", return_value="fc-1"),
    ):
        return client.post("/items", json={"url": url}, headers=KEY)


def test_post_requires_key():
    r = client.post("/items", json={"url": "https://example.test"})
    assert r.status_code == 401


def test_post_creates_generating_item():
    r = _create()
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "generating"
    assert body["title"] == "Title"
    assert body["id"].startswith("itm_")
    assert body["audio_url"] is None


def test_post_extraction_failure_lands_failed():
    with patch("app.endpoints.items.extract_article", side_effect=ExtractionError("bad url")):
        r = client.post("/items", json={"url": "https://example.test"}, headers=KEY)
    body = r.json()
    assert body["status"] == "failed"
    assert "extraction" in body["error"]


def test_get_polls_to_ready_and_serves_audio():
    item_id = _create().json()["id"]
    result = SynthesisResult(
        audio_base64=base64.b64encode(b"OggS-fake-bytes").decode(),
        format="audio/ogg",
        sample_rate=24000,
        duration=6.0,
        paragraphs=[
            {"index": 0, "start": 0.0, "end": 3.0, "text": "p1"},
            {"index": 1, "start": 3.0, "end": 6.0, "text": "p2"},
        ],
    )
    with patch("app.endpoints.items.poll_synthesis", return_value=("ready", result)):
        r = client.get(f"/items/{item_id}", headers=KEY)
    body = r.json()
    assert body["status"] == "ready"
    assert body["duration"] == 6.0
    assert body["audio_url"] == f"/items/{item_id}/audio"
    # the display markdown is joined onto the timeline by index, not the spoken text
    assert body["paragraphs"][0]["text"] == "**p1**"
    assert body["paragraphs"][1]["text"] == "p2"

    audio = client.get(f"/items/{item_id}/audio", headers=KEY)
    assert audio.status_code == 200


def test_audio_requires_key():
    item_id = _create().json()["id"]
    r = client.get(f"/items/{item_id}/audio")
    assert r.status_code == 401


def test_get_storage_failure_lands_failed():
    item_id = _create().json()["id"]
    result = SynthesisResult(
        audio_base64=base64.b64encode(b"OggS-fake-bytes").decode(),
        format="audio/ogg",
        sample_rate=24000,
        duration=3.0,
        paragraphs=[{"index": 0, "start": 0.0, "end": 3.0, "text": "p1"}],
    )
    with (
        patch("app.endpoints.items.poll_synthesis", return_value=("ready", result)),
        patch("app.endpoints.items.store_result", side_effect=RuntimeError("bucket down")),
    ):
        r = client.get(f"/items/{item_id}", headers=KEY)
    body = r.json()
    assert body["status"] == "failed"
    assert "store" in body["error"]
    assert "bucket down" in body["error"]


def test_get_alignment_mismatch_lands_failed():
    # display has two units but the timeline returns one — the join guard trips
    item_id = _create().json()["id"]
    result = SynthesisResult(
        audio_base64=base64.b64encode(b"OggS-fake-bytes").decode(),
        format="audio/ogg",
        sample_rate=24000,
        duration=3.0,
        paragraphs=[{"index": 0, "start": 0.0, "end": 3.0, "text": "p1"}],
    )
    with patch("app.endpoints.items.poll_synthesis", return_value=("ready", result)):
        r = client.get(f"/items/{item_id}", headers=KEY)
    body = r.json()
    assert body["status"] == "failed"
    assert "store" in body["error"]
    assert "alignment mismatch" in body["error"]


def test_get_polls_to_failed():
    item_id = _create().json()["id"]
    with patch("app.endpoints.items.poll_synthesis", return_value=("failed", "RuntimeError: forced failure")):
        r = client.get(f"/items/{item_id}", headers=KEY)
    body = r.json()
    assert body["status"] == "failed"
    assert "forced failure" in body["error"]


def test_get_unknown_item_404():
    r = client.get("/items/itm_nope", headers=KEY)
    assert r.status_code == 404


def test_audio_unavailable_when_not_ready():
    item_id = _create().json()["id"]
    r = client.get(f"/items/{item_id}/audio", headers=KEY)
    assert r.status_code == 404


def test_audio_unknown_item_404():
    r = client.get("/items/itm_nope/audio", headers=KEY)
    assert r.status_code == 404


def test_health_is_public():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
