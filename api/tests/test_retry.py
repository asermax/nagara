"""POST /items/{id}/retry: re-drive a failed item, resuming from the phase that failed.

The seam is the HTTP surface. The 409 lands on each non-retryable status and past the
cap, queued_at moves on every attempt, and the concurrent double-click cannot both win.
The resume rows key on ``enriched_at``: the zero-cost row re-enters at the generating
phase with no fetch and no extraction spawn at all, and an unfinished row re-drives the
full source step (the handle rules live in test_extraction_retry).
"""
import asyncio
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from app.helpers import now_iso
from app.main import app
from app.service.lifecycle import claim_for_retry

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

_UNITS_DICTS = [
    {"type": "paragraph", "display": "**p1**", "spoken": "p1"},
    {"type": "paragraph", "display": "p2", "spoken": "p2"},
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
    # generating and failed downstream (poll crash, store failure). Retry re-enters at
    # the generating phase — no fetch, no extraction spawn, no resolve — so neither the
    # firecrawl fetch nor the extraction client is ever entered; the spoken text already
    # lives on the row, and poll drives the synthesis from here.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, modal_call_id="fc-old")
    with (
        patch("app.service.pipeline.steps.FirecrawlFetcher") as fetcher,
        patch("app.service.pipeline.steps.spawn_extraction", new_callable=AsyncMock) as spawn_extraction,
        patch("app.service.pipeline.steps.resolve_extraction", new_callable=AsyncMock) as resolve_extraction,
    ):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    fetcher.assert_not_called()
    spawn_extraction.assert_not_called()
    resolve_extraction.assert_not_called()

    row = _fetch("SELECT status, retry_count, error FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"  # promoted straight to the poll-driven phase
    assert row[1] == 1  # retry_count advanced
    assert row[2] is None  # the old error is cleared


# --- the two re-enrich resume rows: enriched_at null ---------------------------


def test_retry_partial_units_resumes_at_describe():
    # enriched_at null but units present: the extraction already resolved and its units
    # survive on the row, so the retry promotes straight to the generating phase — no
    # re-fetch, no new job — and describe picks up where it failed.
    item_id = _insert_item(enriched_at=None, units=_UNITS_DICTS)
    with (
        patch("app.service.pipeline.steps.FirecrawlFetcher") as fetcher,
        patch("app.service.pipeline.steps.spawn_extraction", new_callable=AsyncMock) as spawn_extraction,
    ):
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    fetcher.assert_not_called()
    spawn_extraction.assert_not_called()
    row = _fetch("SELECT status, extraction_handle, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"
    assert row[1] is None  # never re-minted: the job completed before the failure
    assert row[2] == 1


def test_retry_no_units_full_enrichment(stub_enqueue):
    # enriched_at null and no units: the total-loss row. Full cost — one fetch and a
    # fresh spawn — because nothing survived the failure.
    item_id = _insert_item(enriched_at=None, units=None)
    with stub_enqueue():
        r = client.post(f"/items/{item_id}/retry", headers=KEY)

    assert r.status_code == 202
    row = _fetch("SELECT status, extraction_handle, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"
    assert row[1] == f"{item_id}-1"
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
    client.post(f"/items/{item_id}/retry", headers=KEY)
    new = _fetch("SELECT queued_at FROM items WHERE id = ?", (item_id,))[0]
    assert new != old
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(new)).total_seconds() < 5


def test_retry_advances_retry_count_each_attempt():
    # Each successful retry advances the count; the cap reads it on the next call.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, retry_count=1)
    client.post(f"/items/{item_id}/retry", headers=KEY)
    count = _fetch("SELECT retry_count FROM items WHERE id = ?", (item_id,))[0]
    assert count == 2


# --- response shape ------------------------------------------------------------


def test_retry_returns_item_response():
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS)
    r = client.post(f"/items/{item_id}/retry", headers=KEY)
    body = r.json()
    assert body["id"] == item_id
    assert body["status"] == "queued"  # captured before the background task advances it
    assert body["audio_url"] is None


# --- concurrency: two retries on one item must not double-spawn ----------------


@pytest.mark.anyio
async def test_concurrent_retries_spawn_once_and_count_once():
    # The check-then-write race: two retries that both read the failed row before either
    # writes must still schedule one task, not two. The atomic conditional UPDATE in
    # claim_for_retry is the arbiter; a barrier forces the worst-case interleaving (both
    # reads complete before either transition) so the test reliably reproduces the race a
    # real double-click would trigger.
    item_id = _insert_item(enriched_at=now_iso(), units=_UNITS_DICTS, retry_count=0)

    barrier = asyncio.Barrier(2)

    async def syncing_claim(db, item_id):
        await barrier.wait()
        return await claim_for_retry(db, item_id)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        with patch("app.endpoints.items.claim_for_retry", syncing_claim):
            responses = await asyncio.gather(
                ac.post(f"/items/{item_id}/retry", headers=KEY),
                ac.post(f"/items/{item_id}/retry", headers=KEY),
            )

    assert sorted(r.status_code for r in responses) == [202, 409]  # exactly one retry wins

    row = _fetch("SELECT status, retry_count FROM items WHERE id = ?", (item_id,))
    assert row[0] == "generating"  # the winner's task drove it, once
    assert row[1] == 1  # incremented once in SQL, not overwritten by a stale read
