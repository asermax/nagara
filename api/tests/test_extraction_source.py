"""POST /items — the source step: fetch, mint, spawn.

Rows B1-B6 of the test design (.scratch/extraction-v2/test-design/api.md). The queued
task runs inside the TestClient request; the firecrawl fetch and the extraction spawn
replay off fabricated cassettes built from the boundary contract, and the unreachable
case dials a real refused connection with no cassette in play.
"""
import asyncio
import os
import sqlite3
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.helpers import now_iso
from app.main import app
from app.service.fetch import FetchedPage
from app.service.lifecycle import advance_queued_item

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

_URL = "https://source.test/article"
_HTML = "<html><head></head><body><article><h1>The Article Title</h1><p>First paragraph of the article body.</p></article></body></html>"


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


def _seed_recipe(domain: str = "source.test", script: str = "// seeded script v1") -> str:
    # The test database is one sqlite per session, so a second seed of the same domain
    # reuses the row it already has rather than violating the (domain, version) pair.
    existing = _fetch("SELECT id FROM recipe_versions WHERE domain = ? AND version = 1", (domain,))
    if existing is not None:
        return existing[0]
    recipe_id = "rcp_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO recipe_versions (id, domain, version, script, created_at) VALUES (?, ?, 1, ?, ?)",
        (recipe_id, domain, script, now_iso()),
    )
    return recipe_id


def _row(item_id: str):
    return _fetch(
        "SELECT status, extraction_handle, extraction_domain, recipe_version_id, error "
        "FROM items WHERE id = ?",
        (item_id,),
    )


# --- B1: a known domain spawns with its recipe ---------------------------------


@pytest.mark.vcr
def test_a_spawned_item_moves_to_generating_with_handle_and_recipe_version():
    recipe_id = _seed_recipe()

    created = client.post("/items", json={"url": _URL}, headers=KEY).json()

    assert created["status"] == "queued"  # serialized before the task ran
    status, handle, domain, pointer, error = _row(created["id"])
    assert status == "generating"
    assert handle == created["id"]  # the handle is the item id, unchanged
    assert domain == "source.test"
    assert pointer == recipe_id  # the version whose script was sent


# --- B2: a fresh domain spawns with no recipe -----------------------------------


@pytest.mark.vcr
def test_a_fresh_domain_spawns_with_no_recipe(vcr):
    created = client.post("/items", json={"url": "https://freshdomain.test/post"}, headers=KEY).json()

    status, handle, _domain, pointer, _error = _row(created["id"])
    assert status == "generating"
    assert handle == created["id"]

    spawn = next(r for r in vcr.requests if r.host == "extraction.test")
    body = spawn.body.decode()
    assert '"recipe"' not in body  # absent means author: nothing was sent
    assert _pointer_is_null(created["id"])


def _pointer_is_null(item_id: str) -> bool:
    return _fetch("SELECT recipe_version_id FROM items WHERE id = ?", (item_id,))[0] is None


# --- B3: a surviving handle advances on the conflict ----------------------------


@pytest.mark.vcr
def test_an_existing_handle_advances_on_the_conflict():
    # The row a spawn left behind without confirming: queued, handle already minted and
    # persisted. Re-running the source step over it re-attaches — the spawn's 409 is the
    # id already existing — and the item proceeds on the same handle.
    item_id = "itm_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO items (id, url, status, voice, created_at, queued_at, extraction_handle, extraction_domain) "
        "VALUES (?, ?, 'queued', 'af_heart', ?, ?, 'itm_00000003', 'source.test')",
        (item_id, _URL, now_iso(), now_iso()),
    )
    _seed_recipe()

    asyncio.run(advance_queued_item(item_id))
    status, handle, _domain, _pointer, _error = _row(item_id)
    assert status == "generating"
    assert handle == "itm_00000003"  # unchanged: the conflict kept the existing job


# --- B4: html over the cap fails the item ---------------------------------------


@pytest.mark.vcr
def test_html_over_the_cap_fails_the_item():
    created = client.post("/items", json={"url": _URL}, headers=KEY).json()

    status, handle, _domain, _pointer, error = _row(created["id"])
    assert status == "failed"
    assert error is not None and error.startswith("extraction:")
    assert handle == created["id"]  # the mint persisted before the spawn refused it


# --- B5: an unreachable service fails the item retryably -------------------------


def test_an_unreachable_service_fails_the_item_retryably(monkeypatch):
    # No cassette: the client dials 127.0.0.1:1 for real and the connection is refused.
    # The item fails with the spawn step's extraction: prefix and stays retryable.
    monkeypatch.setattr(settings, "cloudflare_extraction_url", "http://127.0.0.1:1")

    class _Fetched:
        def __init__(self, *_args):
            pass

        def fetch(self, url):
            return FetchedPage(html=_HTML, url=url, source="firecrawl")

    with patch("app.service.pipeline.steps.FirecrawlFetcher", _Fetched):
        created = client.post("/items", json={"url": _URL}, headers=KEY).json()

    status, handle, _domain, _pointer, error = _row(created["id"])
    assert status == "failed"
    assert error is not None and error.startswith("extraction:")

    retried = client.post(f"/items/{created['id']}/retry", headers=KEY)
    assert retried.status_code == 202  # failed and under the cap: retryable


# --- B6: a failed fetch fails the item with the fetch prefix ---------------------


@pytest.mark.vcr
def test_a_failed_fetch_fails_the_item_with_the_fetch_prefix():
    created = client.post("/items", json={"url": _URL}, headers=KEY).json()

    status, handle, _domain, _pointer, error = _row(created["id"])
    assert status == "failed"
    assert error == "fetch: firecrawl unreachable"
    assert handle is None  # the mint only lands after a successful fetch
