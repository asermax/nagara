"""Seam 1 (HTTP surface, TestClient) for the cost ledger.

The firecrawl case replays the one recorded firecrawl cassette (reused from
test_firecrawl_fetch) through the real enqueue path, so the CostEntry is written by the
lifecycle exactly as production would. The tts case drives an item to ready with the
extraction resolve and the tts poll stubbed at the seams the pipeline reaches them.
Neither asserts a total against a hardcoded number — prices are configuration, so the
dollar figure is derived from the same Settings the code reads.
"""
import base64
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.schemas.extraction import JobStatus
from app.schemas.tts import SynthesisResult

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

# The recorded firecrawl cassette: the request body must match the recording, so the URL
# is the one the cassette was recorded against. The pipeline's fetch is always firecrawl
# now, so nothing is forced — the enqueue path itself is the metering point.
_FIRECRAWL_URL = "https://httpbin.org/html"
_FIRECRAWL_CASSETTE = str(
    Path(__file__).resolve().parent / "cassettes" / "test_firecrawl_fetch" / "test_firecrawl_http_surface.yaml"
)

_HTML = "<html><head></head><body><article><h1>title</h1><p>p1</p><p>p2</p></article></body></html>"
_COMPLETE = JobStatus(
    state="complete",
    title="Title",
    units=[
        {"type": "paragraph", "display": "p1"},
        {"type": "paragraph", "display": "p2"},
    ],
)
_TTS_RESULT = SynthesisResult(
    audio_base64=base64.b64encode(b"OggS-fake-bytes").decode(),
    format="audio/ogg",
    sample_rate=24000,
    duration=6.0,
    paragraphs=[
        {"index": 0, "start": 0.0, "end": 3.0, "text": "p1"},
        {"index": 1, "start": 3.0, "end": 6.0, "text": "p2"},
    ],
)


def _db_path() -> Path:
    return Path(os.environ["NAGARA_DATA_DIR"]) / "test.db"


def _fetch(sql: str, params: tuple = ()):
    with sqlite3.connect(str(_db_path())) as conn:
        return conn.execute(sql, params).fetchone()


def _create(stub_enqueue) -> str:
    # The enqueue path with the fetch stubbed and the spawn accepted: the item lands
    # generating with the units still to arrive.
    with (
        stub_enqueue(_HTML),
        patch("app.service.tts.spawn_synthesis", return_value="fc-cost"),
    ):
        return client.post("/items", json={"url": "https://example.test/post"}, headers=KEY).json()["id"]


def _poll_to_ready(item_id: str) -> None:
    with (
        patch("app.service.pipeline.steps.resolve_extraction", new_callable=AsyncMock, return_value=_COMPLETE),
        patch("app.service.tts.spawn_synthesis", return_value="fc-cost"),
        patch("app.service.tts.poll_synthesis", return_value=("ready", _TTS_RESULT)),
    ):
        client.get(f"/items/{item_id}", headers=KEY)


@pytest.mark.vcr(_FIRECRAWL_CASSETTE)
def test_enqueue_records_a_firecrawl_cost_entry(vcr):
    # The fetch is the only recorded request — the spawn is stubbed — and everything below
    # the route runs for real, so the CostEntry is written by the lifecycle, priced from
    # Settings.
    with (
        patch("app.config.settings.firecrawl_api_key", "replay-key"),
        patch("app.service.pipeline.steps.spawn_extraction", new_callable=AsyncMock, return_value=True),
    ):
        item_id = client.post("/items", json={"url": _FIRECRAWL_URL}, headers=KEY).json()["id"]

    row = _fetch(
        "SELECT quantity, unit, dollars, detail FROM cost_entries WHERE item_id = ? AND type = 'firecrawl'",
        (item_id,),
    )
    assert row is not None
    assert row[0] == 1  # creditsUsed the cassette reported
    assert row[1] == "credits"
    assert row[2] == pytest.approx(1 * settings.firecrawl_dollars_per_credit)
    detail = json.loads(row[3])
    assert detail["proxy"] == "basic"
    assert "httpbin.org" in detail["destination"]


def test_ready_item_records_a_tts_cost_entry(stub_enqueue):
    item_id = _create(stub_enqueue)
    _poll_to_ready(item_id)

    row = _fetch(
        "SELECT quantity, unit, dollars, detail FROM cost_entries WHERE item_id = ? AND type = 'tts'",
        (item_id,),
    )
    assert row is not None
    assert row[0] == 6.0
    assert row[1] == "seconds"
    assert row[2] == pytest.approx(6.0 * settings.tts_dollars_per_second)
    assert json.loads(row[3])["duration"] == 6.0
