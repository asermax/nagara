import asyncio
import base64
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.helpers import now_iso
from app.main import app
from app.schemas.items import ParagraphUnit
from app.schemas.tts import SynthesisResult
from app.service.extract import ExtractionError
from app.service.lifecycle import advance_queued_item
from app.service.tts import VOICE_POOL

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

_UNITS = [
    ParagraphUnit(type="paragraph", display="**p1**", spoken="p1"),
    ParagraphUnit(type="paragraph", display="p2", spoken="p2"),
]


def _db_path() -> Path:
    return Path(os.environ["NAGARA_DATA_DIR"]) / "test.db"


def _exec(sql: str, params: tuple = ()) -> None:
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute(sql, params)
        conn.commit()


def _fetch(sql: str, params: tuple = ()):
    with sqlite3.connect(str(_db_path())) as conn:
        return conn.execute(sql, params).fetchone()


def _insert_item(status: str = "queued", queued_at: str | None = None) -> str:
    item_id = "itm_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO items (id, url, status, voice, created_at, queued_at) "
        "VALUES (?, ?, ?, 'af_heart', ?, ?)",
        (item_id, "https://example.test", status, now_iso(), queued_at),
    )
    return item_id


def _create(url="https://example.test/post", voice=None):
    payload = {"url": url}
    if voice is not None:
        payload["voice"] = voice
    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", _UNITS)),
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-1"),
    ):
        return client.post("/items", json=payload, headers=KEY)


def test_post_requires_key():
    r = client.post("/items", json={"url": "https://example.test"})
    assert r.status_code == 401


def test_post_returns_queued_then_advances_to_generating():
    r = _create()
    assert r.status_code == 202
    body = r.json()
    # the response is serialized from the queued item before the background task runs
    assert body["status"] == "queued"
    assert body["title"] is None
    assert body["id"].startswith("itm_")
    assert body["audio_url"] is None
    assert body["units"] is None  # never on the wire while queued

    # TestClient ran the task to completion inline; a following GET observes generating.
    with patch("app.endpoints.items.poll_synthesis", return_value=("generating", None)):
        polled = client.get(f"/items/{body['id']}", headers=KEY)
    polled_body = polled.json()
    assert polled_body["status"] == "generating"
    assert polled_body["title"] == "Title"
    assert polled_body["units"] is None  # held back until timing is joined at ready


def test_post_without_voice_picks_from_pool():
    voice = _create().json()["voice"]
    assert voice in VOICE_POOL


def test_post_with_voice_uses_it():
    body = _create(voice="am_onyx").json()
    assert body["voice"] == "am_onyx"


def test_voice_is_stable_across_polls():
    created = _create().json()
    with patch("app.endpoints.items.poll_synthesis", return_value=("generating", None)):
        polled = client.get(f"/items/{created['id']}", headers=KEY)
    assert polled.json()["voice"] == created["voice"]


def test_queued_at_is_set_at_enqueue():
    # queued_at is written in the enqueue commit, not by the task, so the row carries a
    # clock even when the task never advances it — the ceiling can always reap a row whose
    # task died before it ran. The task no longer writes queued_at, so its presence here
    # is the enqueue write alone.
    with patch("app.service.lifecycle.extract_article", side_effect=ExtractionError("nope")):
        created = client.post("/items", json={"url": "https://example.test"}, headers=KEY).json()
    row = _fetch("SELECT queued_at, status FROM items WHERE id = ?", (created["id"],))
    assert row[0] is not None
    assert row[1] == "failed"


def test_queued_item_units_are_null_on_wire():
    # A queued item the task has not reached: no units on the row, none on the wire.
    item_id = _insert_item(status="queued")
    body = client.get(f"/items/{item_id}", headers=KEY).json()
    assert body["status"] == "queued"
    assert body["units"] is None
    assert body["audio_url"] is None


def test_post_extraction_failure_lands_failed():
    with patch("app.service.lifecycle.extract_article", side_effect=ExtractionError("bad url")):
        r = client.post("/items", json={"url": "https://example.test"}, headers=KEY)
    body = r.json()
    assert body["status"] == "queued"  # response captured before the task ran
    # the task ran inline and failed the item
    failed = client.get(f"/items/{body['id']}", headers=KEY).json()
    assert failed["status"] == "failed"
    assert "extraction" in failed["error"]


def test_task_spawn_failure_lands_failed():
    units = [ParagraphUnit(type="paragraph", display="p1", spoken="p1")]
    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", units)),
        patch("app.service.lifecycle.spawn_synthesis", side_effect=RuntimeError("modal down")),
    ):
        created = client.post("/items", json={"url": "https://example.test"}, headers=KEY).json()
    failed = client.get(f"/items/{created['id']}", headers=KEY).json()
    assert failed["status"] == "failed"
    assert "spawn" in failed["error"]
    assert "modal down" in failed["error"]


def test_poll_fails_queued_past_ceiling():
    stale = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    item_id = _insert_item(status="queued", queued_at=stale)
    body = client.get(f"/items/{item_id}", headers=KEY).json()
    assert body["status"] == "failed"
    assert "enrichment" in body["error"]
    assert "300" in body["error"]


def test_poll_leaves_queued_within_ceiling():
    fresh = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    item_id = _insert_item(status="queued", queued_at=fresh)
    body = client.get(f"/items/{item_id}", headers=KEY).json()
    assert body["status"] == "queued"


def test_poll_reaps_queued_stranded_before_task_ran():
    # A row stranded at queued (container died before the task ran) is reaped at the
    # ceiling: queued_at is set at enqueue, so the clock runs whether or not the task
    # ever picked the item up. This is the case the old no-clock test asserted the wrong
    # behaviour for.
    stale = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    item_id = _insert_item(status="queued", queued_at=stale)
    body = client.get(f"/items/{item_id}", headers=KEY).json()
    assert body["status"] == "failed"
    assert "enrichment" in body["error"]


def test_late_task_does_not_resurrect_failed():
    # The task runs inline. extract succeeds; spawn simulates poll firing the ceiling
    # (fails the item) before returning. The task's generating write must then be abandoned
    # — a late task commits nothing over a failure it did not cause.
    def spawn_after_ceiling(paragraphs, voice):
        _exec(
            "UPDATE items SET status = 'failed', error = ? WHERE status = 'queued'",
            ("enrichment: no result after 300s",),
        )
        return "fc-late"

    units = [ParagraphUnit(type="paragraph", display="p1", spoken="p1")]
    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", units)),
        patch("app.service.lifecycle.spawn_synthesis", side_effect=spawn_after_ceiling),
    ):
        created = client.post("/items", json={"url": "https://example.test"}, headers=KEY).json()

    row = _fetch(
        "SELECT status, error, modal_call_id, units FROM items WHERE id = ?",
        (created["id"],),
    )
    assert row[0] == "failed"  # not resurrected to generating
    assert row[1] == "enrichment: no result after 300s"  # poll's error preserved
    assert row[2] is None  # the generating transition wrote nothing
    assert row[3] is None


def test_task_abandons_when_item_already_left_queued():
    # A task that fires after the item already advanced does no work and writes nothing.
    created = _create().json()  # task ran inline, item is now generating
    item_id = created["id"]

    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", _UNITS)) as mock_extract,
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-x"),
    ):
        asyncio.run(advance_queued_item(item_id))

    mock_extract.assert_not_called()
    row = _fetch("SELECT status FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"  # unchanged


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
    units = body["units"]
    # the display markdown is joined onto the timeline by index, with spoken projected out
    assert units[0]["display"] == "**p1**"
    assert units[1]["display"] == "p2"
    assert units[0]["type"] == "paragraph"
    assert all("spoken" not in u for u in units)
    assert all("image" not in u for u in units)  # no image key at all, not a null one

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
