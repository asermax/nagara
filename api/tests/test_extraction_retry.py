"""POST /items/{id}/retry — the handle rule across retries.

Rows B14-B19 of the test design. One merge rule by the prior failure's source: the
handle is stable, a new id is minted only when the previous job ended error, the
not_article verdict is accepted under the cap and stands, the spawn-outcome-unknown row
re-spawns the same handle and takes 201 or 409 alike, and an enriched row never touches
the extraction pipeline at all.
"""
import base64
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.helpers import now_iso
from app.main import app
from app.schemas.tts import SynthesisResult

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

_URL = "https://retry.test/article"

_UNITS_DICTS = [
    {"type": "paragraph", "display": "**p1**", "spoken": "p1"},
    {"type": "paragraph", "display": "p2", "spoken": "p2"},
]


@pytest.fixture(autouse=True)
def _extraction_service(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_extraction_url", "https://extraction.test")
    monkeypatch.setattr(settings, "firecrawl_api_key", "replay-key")


def _db_path() -> Path:
    return Path(os.environ["NAGARA_DATA_DIR"]) / "test.db"


def _exec(sql: str, params: tuple = ()) -> None:
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute(sql, params)
        conn.commit()


def _fetch(sql: str, params: tuple = ()):
    with sqlite3.connect(str(_db_path())) as conn:
        return conn.execute(sql, params).fetchone()


def _seed_recipe() -> str:
    existing = _fetch("SELECT id FROM recipe_versions WHERE domain = 'retry.test' AND version = 1")
    if existing is not None:
        return existing[0]
    recipe_id = "rcp_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO recipe_versions (id, domain, version, script, created_at) VALUES (?, 'retry.test', 1, '// seeded script v1', ?)",
        (recipe_id, now_iso()),
    )
    return recipe_id


def _insert_item(
    *,
    status: str,
    handle: str | None = None,
    enriched_at: str | None = None,
    units: list | None = None,
    retry_count: int = 0,
    queued_at: str | None = None,
    error: str | None = None,
) -> str:
    item_id = "itm_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO items (id, url, status, voice, created_at, queued_at, enriched_at, units, "
        "retry_count, extraction_handle, extraction_domain, error) "
        "VALUES (?, ?, ?, 'af_heart', ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            item_id,
            _URL,
            status,
            now_iso(),
            queued_at or now_iso(),
            enriched_at,
            json.dumps(units) if units is not None else None,
            retry_count,
            handle,
            "retry.test" if handle is not None else None,
            error,
        ),
    )
    return item_id


def _row(item_id: str):
    return _fetch(
        "SELECT status, extraction_handle, retry_count, error FROM items WHERE id = ?",
        (item_id,),
    )


# --- B14: the error terminal is the one that remints -----------------------------


@pytest.mark.vcr
def test_an_error_terminal_remints_the_handle_and_reruns_extraction():
    _seed_recipe()
    item_id = _insert_item(status="generating", handle="itm_0000000e")

    first = client.get(f"/items/{item_id}", headers=KEY).json()
    assert first["status"] == "failed"
    assert first["error"] == "extraction: revision exhausted after two retries"

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202

    status, handle, count, error = _row(item_id)
    assert status == "generating"
    assert handle == f"{item_id}-1"  # a new id, suffixed by the attempt
    assert count == 1
    assert error is None
    # the cassette match is the wire proof: its spawn entry carries a -1-suffixed job id
    # under the itm_-normalizing matcher, so an unsuffixed re-spawn would not have replayed

    # the new job is what answers from here: it re-runs extraction
    second = client.get(f"/items/{item_id}", headers=KEY).json()
    assert second["status"] == "generating"


# --- B15: a ceiling death re-attaches to the alive job ----------------------------


@pytest.mark.vcr
def test_a_ceiling_death_reattaches_to_the_alive_job():
    _seed_recipe()
    stale = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    item_id = _insert_item(status="generating", handle="itm_0000000f", queued_at=stale)

    first = client.get(f"/items/{item_id}", headers=KEY).json()
    assert first["status"] == "failed"  # the ceiling, with the job unread

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202

    status, handle, count, _error = _row(item_id)
    assert status == "generating"
    assert handle == "itm_0000000f"  # the same id: the job never ended error
    assert count == 1

    # generating waits: the alive job is still running
    second = client.get(f"/items/{item_id}", headers=KEY).json()
    assert second["status"] == "generating"


# --- B16: the not_article verdict stands -------------------------------------------


@pytest.mark.vcr
def test_a_not_article_verdict_stands_across_retries():
    item_id = _insert_item(status="generating", handle="itm_00000010")

    first = client.get(f"/items/{item_id}", headers=KEY).json()
    assert first["status"] == "failed"
    assert first["error"] == "extraction: not an article"

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202  # accepted under the cap, verdict included

    # the retry re-attached: the verdict is the job's own state, so the item holds on
    # the same job rather than starting a new one
    status, handle, count, _error = _row(item_id)
    assert status == "generating"
    assert handle == "itm_00000010"
    assert count == 1

    second = client.get(f"/items/{item_id}", headers=KEY).json()
    assert second["status"] == "failed"
    assert second["error"] == "extraction: not an article"  # the verdict stood

    _status, handle, count, error = _row(item_id)
    assert handle == "itm_00000010"  # still re-attached
    assert count == 1  # one retry consumed
    assert error == "extraction: not an article"


# --- B17: a fetch failure retries into a fresh mint --------------------------------


@pytest.mark.vcr
def test_a_fetch_failure_retry_fetches_and_mints_a_handle():
    _seed_recipe()
    item_id = _insert_item(status="failed", handle=None, error="fetch: firecrawl unreachable")

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202

    status, handle, count, error = _row(item_id)
    assert status == "generating"
    assert handle == f"{item_id}-1"  # minted on the retry attempt
    assert count == 1
    assert error is None


# --- B18: an unknown spawn outcome re-spawns the same handle -----------------------


@pytest.mark.vcr
def test_an_unknown_spawn_outcome_respawns_the_same_handle():
    _seed_recipe()
    # The row a spawn left behind when its outcome never came back: failed with the
    # handle already persisted. The retry re-spawns that handle and takes the conflict
    # as happily as a create.
    item_id = _insert_item(
        status="failed",
        handle="itm_00000012",
        error="extraction: ConnectError: connection refused",
    )

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202

    status, handle, count, error = _row(item_id)
    assert status == "generating"
    assert handle == "itm_00000012"  # the same id the unknown spawn carried
    assert count == 1
    assert error is None


# --- B19: an enriched row never touches the extraction pipeline ---------------------


def test_an_enriched_retry_never_calls_the_extraction_pipeline():
    item_id = _insert_item(
        status="failed",
        handle=None,
        enriched_at=now_iso(),
        units=_UNITS_DICTS,
        error="tts: crashed on the GPU",
    )

    with (
        patch("app.service.pipeline.steps.spawn_extraction", new_callable=AsyncMock) as spawn,
        patch("app.service.pipeline.steps.resolve_extraction", new_callable=AsyncMock) as resolve,
        patch("app.service.pipeline.steps.FirecrawlFetcher") as fetcher,
        patch("app.service.tts.spawn_synthesis", return_value="fc-19"),
        patch("app.service.tts.poll_synthesis", return_value=("generating", None)),
    ):
        retried = client.post(f"/items/{item_id}/retry", headers=KEY)
        assert retried.status_code == 202

        # no re-fetch, no spawn, no resolve: the row re-enters at the generating phase
        spawn.assert_not_called()
        resolve.assert_not_called()
        fetcher.assert_not_called()

        first = client.get(f"/items/{item_id}", headers=KEY).json()
        assert first["status"] == "generating"  # synthesis spawned, resolution pending
        assert _row(item_id)[0] == "generating"
        assert _fetch("SELECT modal_call_id FROM items WHERE id = ?", (item_id,))[0] == "fc-19"

    result = SynthesisResult(
        audio_base64=base64.b64encode(b"OggS-fake-bytes").decode(),
        format="audio/ogg",
        sample_rate=24000,
        duration=4.0,
        paragraphs=[
            {"index": 0, "start": 0.0, "end": 2.0, "text": "p1"},
            {"index": 1, "start": 2.0, "end": 4.0, "text": "p2"},
        ],
    )
    with patch("app.service.tts.poll_synthesis", return_value=("ready", result)):
        second = client.get(f"/items/{item_id}", headers=KEY).json()
    assert second["status"] == "ready"  # straight through describe (done) and TTS
