"""POST /items/{id}/retry: re-drive a failed item, resuming from the phase that failed.

The seam is the HTTP surface. All three resume rows from the quest table are keyed on
``enriched_at`` and the presence of units, the 409 lands on each non-retryable status and
past the cap, and ``queued_at`` moves on every attempt. The zero-cost row is the one worth
asserting hardest: an ``enriched_at`` set retries with no fetch and no describe call at all.
"""
import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.helpers import now_iso
from app.main import app
from app.schemas.items import ParagraphUnit
from app.service.lifecycle import claim_for_retry

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

# The persisted shape (dicts in the units JSON column) and the in-memory shape extract_article
# returns (pydantic units), kept in step so a row-state insert and an extract mock share text.
_UNITS_DICTS = [
    {"type": "paragraph", "display": "**p1**", "spoken": "p1"},
    {"type": "paragraph", "display": "p2", "spoken": "p2"},
]
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


def _insert_item(
    *,
    status: str = "failed",
    enriched_at: str | None = None,
    units: list | None = None,
    retry_count: int = 0,
    queued_at: str | None = None,
    modal_call_id: str | None = None,
    error: str | None = "tts: crashed on the GPU",
    url: str = "https://example.test/article",
) -> str:
    item_id = "itm_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO items (id, url, status, voice, created_at, queued_at, enriched_at, "
        "units, retry_count, modal_call_id, error) "
        "VALUES (?, ?, ?, 'af_heart', ?, ?, ?, ?, ?, ?, ?)",
        (
            item_id,
            url,
            status,
            now_iso(),
            queued_at or now_iso(),
            enriched_at,
            json.dumps(units) if units is not None else None,
            retry_count,
            modal_call_id,
            error,
        ),
    )
    return item_id


# --- auth + existence ----------------------------------------------------------


def test_retry_requires_key():
    item_id = _insert_item()
    r = client.post(f"/items/{item_id}/retry")
    assert r.status_code == 401


def test_retry_unknown_item_404():
    r = client.post("/items/itm_nope/retry", headers=KEY)
    assert r.status_code == 404


# --- the zero-cost resume row: enriched_at set ---------------------------------


def test_retry_enriched_respawns_without_fetch_or_describe():
    # The row worth asserting hardest. enriched_at set means a previous run reached
    # generating and failed downstream (poll crash, store failure). Retry re-spawns only,
    # straight to generating — no fetch, no segment — so extract_article is never entered.
    # Under cassettes this is no cassette interaction at all: nothing is fetched and nothing
    # is described, the spoken text already lives on the row.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, modal_call_id="fc-old")
    with (
        patch("app.service.lifecycle.extract_article") as mock_extract,
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-new") as mock_spawn,
    ):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    mock_extract.assert_not_called()
    # the re-spawn synthesizes the persisted spoken text, not a fresh extraction
    mock_spawn.assert_called_once_with(["p1", "p2"], "af_heart")

    row = _fetch(
        "SELECT status, modal_call_id, retry_count, error FROM items WHERE id = ?",
        (item_id,),
    )
    assert row[0] == "generating"  # re-spawned straight through, never back to queued work
    assert row[1] == "fc-new"  # fresh handle; the crashed one is replaced
    assert row[2] == 1  # retry_count advanced
    assert row[3] is None  # the old error is cleared


# --- the two re-enrich resume rows: enriched_at null ---------------------------


def test_retry_partial_units_re_enriches():
    # enriched_at null but units present: back to queued and re-driven. Enrichment steps are
    # not built yet, so today this re-extracts fully; the units-present distinction is what
    # the future per-unit resume keys on. What matters here is the row is handled: it goes
    # back through fetch and lands generating.
    item_id = _insert_item(enriched_at=None, units=_UNITS_DICTS)
    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", _UNITS)),
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-2"),
    ):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    row = _fetch("SELECT status, modal_call_id, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"
    assert row[1] == "fc-2"
    assert row[2] == 1


def test_retry_no_units_full_enrichment():
    # enriched_at null and no units: the total-loss row. Full cost — one fetch — because
    # nothing survived the failure.
    item_id = _insert_item(enriched_at=None, units=None)
    with (
        patch("app.service.lifecycle.extract_article", return_value=("Title", _UNITS)),
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-3"),
    ):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    row = _fetch("SELECT status, modal_call_id, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"
    assert row[1] == "fc-3"
    assert row[2] == 1


# --- 409 on every non-retryable status -----------------------------------------


def test_retry_refuses_queued():
    item_id = _insert_item(status="queued")
    r = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert r.status_code == 409


def test_retry_refuses_generating():
    item_id = _insert_item(status="generating", modal_call_id="fc-running")
    r = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert r.status_code == 409


def test_retry_refuses_ready():
    item_id = _insert_item(status="ready", modal_call_id="fc-done", error=None)
    r = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert r.status_code == 409


def test_retry_409_leaves_the_row_untouched():
    # A refusal writes nothing: a concurrent caller is not nudged toward a new state.
    item_id = _insert_item(status="ready", modal_call_id="fc-done", error=None, retry_count=0)
    client.post(f"/items/{item_id}/retry", headers=KEY)
    row = _fetch("SELECT status, retry_count, queued_at FROM items WHERE id = ?", (item_id,))
    assert row[0] == "ready"
    assert row[1] == 0


# --- the cap -------------------------------------------------------------------


def test_retry_refuses_past_cap():
    # retry_count at the cap (default 3) is 409; the ceiling on the worst case is local.
    item_id = _insert_item(retry_count=3)
    r = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert r.status_code == 409
    assert "retry" in r.json()["detail"].lower()
    # past-cap refuses without advancing the count or touching the row
    row = _fetch("SELECT retry_count, status FROM items WHERE id = ?", (item_id,))
    assert row[0] == 3
    assert row[1] == "failed"


def test_retry_allowed_just_under_cap():
    # retry_count one below the cap is the last allowed attempt and lands.
    item_id = _insert_item(retry_count=2, enriched_at=now_iso(), units=_UNITS_DICTS)
    with patch("app.service.lifecycle.spawn_synthesis", return_value="fc-last"):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert r.status_code == 202
    row = _fetch("SELECT status, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"
    assert row[1] == 3  # now at the cap; a further retry would 409


# --- queued_at moves on every attempt ------------------------------------------


def test_retry_rewrites_queued_at():
    # queued_at is the ceiling's clock and is rewritten on every retry, so a retried item
    # is not instantly stale (created_at never moves and would be). An old clock is replaced.
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, queued_at=old)
    with patch("app.service.lifecycle.spawn_synthesis", return_value="fc-fresh"):
        client.post(f"/items/{item_id}/retry", headers=KEY)
    new = _fetch("SELECT queued_at FROM items WHERE id = ?", (item_id,))[0]
    assert new != old
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(new)).total_seconds() < 5


def test_retry_advances_retry_count_each_attempt():
    # Each successful retry advances the count; the cap reads it on the next call.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, retry_count=1)
    with patch("app.service.lifecycle.spawn_synthesis", return_value="fc-again"):
        client.post(f"/items/{item_id}/retry", headers=KEY)
    count = _fetch("SELECT retry_count FROM items WHERE id = ?", (item_id,))[0]
    assert count == 2


# --- response shape ------------------------------------------------------------


def test_retry_returns_item_response():
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS)
    with patch("app.service.lifecycle.spawn_synthesis", return_value="fc-r"):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)
    body = r.json()
    assert body["id"] == item_id
    assert body["status"] == "queued"  # captured before the background task advances it
    assert body["audio_url"] is None


# --- concurrency: two retries on one item must not double-spawn ----------------


@pytest.mark.anyio
async def test_concurrent_retries_spawn_once_and_count_once():
    # The check-then-write race: two retries that both read the failed row before either
    # writes must still schedule one task and spawn one Modal job, not two. The atomic
    # conditional UPDATE in claim_for_retry is the arbiter; a barrier forces the worst-case
    # interleaving (both reads complete before either transition) so the test reliably
    # reproduces the race a real double-click would trigger.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, retry_count=0)

    barrier = asyncio.Barrier(2)

    async def syncing_claim(db, item_id):
        await barrier.wait()
        return await claim_for_retry(db, item_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        with (
            patch("app.endpoints.items.claim_for_retry", syncing_claim),
            patch("app.service.lifecycle.spawn_synthesis", return_value="fc-race") as mock_spawn,
        ):
            responses = await asyncio.gather(
                ac.post(f"/items/{item_id}/retry", headers=KEY),
                ac.post(f"/items/{item_id}/retry", headers=KEY),
            )

    assert sorted(r.status_code for r in responses) == [202, 409]  # exactly one retry wins
    assert mock_spawn.call_count == 1  # one Modal job, not two — the assertion with money behind it

    row = _fetch("SELECT status, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"  # the winner re-spawned straight through
    assert row[1] == 1  # incremented once in SQL, not overwritten by a stale read
