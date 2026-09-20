"""GET /items/{id} — the generating phase: resolving the extraction job.

Rows B7-B13 of the test design. Poll drives resolve, then describe, then TTS: a
completing job persists its title and units (the spoken form derived on this side,
invariant 1), inserts the recipe it hands back, and continues straight into describe and
synthesis in the same advance. The holds (queued, running) are no-ops under the ceiling,
which fires during them. Modal stays mocked per the suite's habit; the paragraphs in the
cassettes carry no describable units, so the gemini describer is never reached either.
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.helpers import now_iso
from app.main import app

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

pytestmark = pytest.mark.usefixtures("extraction_service")

_TITLE = "The Article Title"
_PARA_DISPLAY = "First paragraph of the article body."
_PARA_DISPLAY_2 = "Second paragraph closing the article."


def _db_path() -> Path:
    return Path(os.environ["NAGARA_DATA_DIR"]) / "test.db"


def _exec(sql: str, params: tuple = ()) -> None:
    with sqlite3.connect(str(_db_path())) as conn:
        conn.execute(sql, params)
        conn.commit()


def _fetch(sql: str, params: tuple = ()):
    with sqlite3.connect(str(_db_path())) as conn:
        return conn.execute(sql, params).fetchone()


def _insert_generating(handle: str, *, recipe_version_id: str | None = None, queued_at: str | None = None) -> str:
    item_id = "itm_" + uuid.uuid4().hex[:8]
    _exec(
        "INSERT INTO items (id, url, status, voice, created_at, queued_at, extraction_handle, extraction_domain, recipe_version_id) "
        "VALUES (?, 'https://example.test/article', 'generating', 'af_heart', ?, ?, ?, 'example.test', ?)",
        (item_id, now_iso(), queued_at or now_iso(), handle, recipe_version_id),
    )
    return item_id


# --- B7: complete, no recipe member ---------------------------------------------


@pytest.mark.vcr
def test_a_complete_job_without_recipe_persists_units_and_drives_describe_and_tts(seed_recipe):
    recipe_id = seed_recipe()
    item_id = _insert_generating("itm_00000007", recipe_version_id=recipe_id)

    with (
        patch("app.service.tts.spawn_synthesis", return_value="fc-7") as spawn,
        patch("app.service.tts.poll_synthesis", return_value=("generating", None)),
    ):
        body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "generating"
    assert body["units"] is None  # held back until timing is joined at ready

    row = _fetch(
        "SELECT title, units, enriched_at, modal_call_id, extraction_handle, recipe_version_id FROM items WHERE id = ?",
        (item_id,),
    )
    title, units_json, enriched_at, call_id, handle, pointer = row
    units = json.loads(units_json)
    assert title == _TITLE
    assert enriched_at is not None  # describe finished
    assert call_id == "fc-7"  # synthesis spawned in the same advance
    assert handle is None  # the job is done; later polls resolve synthesis only
    assert pointer == recipe_id  # the pointer stands
    # the spoken form is derived on this side, from the display markdown
    assert [(u["type"], u["display"], u["spoken"]) for u in units] == [
        ("paragraph", _PARA_DISPLAY, _PARA_DISPLAY),
        ("paragraph", _PARA_DISPLAY_2, _PARA_DISPLAY_2),
    ]
    # what was synthesized is the derived spoken text
    assert spawn.call_args.args[0] == [_PARA_DISPLAY, _PARA_DISPLAY_2]
    # no new recipe version: the job validated the one it was sent
    assert _fetch("SELECT COUNT(*) FROM recipe_versions WHERE domain = 'example.test'")[0] == 1


# --- B8: complete, recipe present ------------------------------------------------


@pytest.mark.vcr
def test_a_complete_job_with_recipe_inserts_the_next_version_and_moves_the_pointer(seed_recipe):
    recipe_id = seed_recipe()
    item_id = _insert_generating("itm_00000008", recipe_version_id=recipe_id)

    with (
        patch("app.service.tts.spawn_synthesis", return_value="fc-8"),
        patch("app.service.tts.poll_synthesis", return_value=("generating", None)),
    ):
        body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "generating"

    pointer = _fetch("SELECT recipe_version_id FROM items WHERE id = ?", (item_id,))[0]
    assert pointer is not None and pointer != recipe_id  # moved
    version, script = _fetch("SELECT version, script FROM recipe_versions WHERE id = ?", (pointer,))
    assert (version, script) == (2, "// the revised recipe v2")  # a pure insert as the next version

    units = json.loads(_fetch("SELECT units FROM items WHERE id = ?", (item_id,))[0])
    # the declared image was acquired: a content hash, and spoken from the author's alt
    image_unit = next(u for u in units if u["type"] == "image")
    assert image_unit["image"]
    assert image_unit["spoken"] == "Image: A chart of requests per second"


# --- B9 / B10: the terminals ------------------------------------------------------


@pytest.mark.vcr
def test_a_not_article_verdict_fails_the_item_and_keeps_the_handle():
    item_id = _insert_generating("itm_00000009")

    body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "failed"
    assert body["error"] == "extraction: not an article"
    # the handle is retained: a retry re-attaches and the verdict stands
    assert _fetch("SELECT extraction_handle FROM items WHERE id = ?", (item_id,))[0] == "itm_00000009"


@pytest.mark.vcr
def test_an_error_terminal_fails_the_item_and_clears_the_handle():
    item_id = _insert_generating("itm_0000000a")

    body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "failed"
    assert body["error"] == "extraction: revision exhausted after two retries"
    # cleared, because that terminal's instance would hand back the same failure: the
    # retry mints a new id
    assert _fetch("SELECT extraction_handle FROM items WHERE id = ?", (item_id,))[0] is None


# --- B11 / B12: the holds ----------------------------------------------------------


@pytest.mark.vcr
def test_a_queued_job_is_a_no_op():
    item_id = _insert_generating("itm_0000000b")

    body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "generating"
    row = _fetch("SELECT title, units, enriched_at, extraction_handle FROM items WHERE id = ?", (item_id,))
    assert row == (None, None, None, "itm_0000000b")  # nothing was written


@pytest.mark.vcr
def test_a_running_job_is_a_no_op():
    item_id = _insert_generating("itm_0000000c")

    body = client.get(f"/items/{item_id}", headers=KEY).json()

    assert body["status"] == "generating"
    row = _fetch("SELECT title, units, enriched_at, extraction_handle FROM items WHERE id = ?", (item_id,))
    assert row == (None, None, None, "itm_0000000c")


# --- B13: the ceiling fires during a hold ------------------------------------------


def test_the_ceiling_fails_a_held_item_mid_authoring_and_leaves_it_retryable():
    # The accepted death: an authoring that outlasts the window kills the item with its
    # job unread — the resolve never runs — and the retry route recovers it.
    stale = (datetime.now(timezone.utc) - timedelta(seconds=301)).isoformat()
    item_id = _insert_generating("itm_0000000d", queued_at=stale)

    with patch("app.service.pipeline.steps.resolve_extraction", new_callable=AsyncMock) as resolve:
        body = client.get(f"/items/{item_id}", headers=KEY).json()

    resolve.assert_not_called()  # the job died unread
    assert body["status"] == "failed"
    assert body["error"] == "enrichment: no result after 300s"

    retried = client.post(f"/items/{item_id}/retry", headers=KEY)
    assert retried.status_code == 202  # failed and under the cap
