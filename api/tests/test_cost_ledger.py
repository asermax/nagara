"""Seam 1 (HTTP surface, TestClient) for the cost ledger.

The firecrawl case replays the one recorded firecrawl cassette (reused from
test_fallback_fetch) through the real enqueue path, so the CostEntry is written by the
lifecycle exactly as production would. The tts case drives an item to ready with a mocked
poll. Neither asserts a total against a hardcoded number — prices are configuration, so the
dollar figure is derived from the same Settings the code reads.
"""
import base64
import json
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app
from app.schemas.items import ParagraphUnit
from app.schemas.tts import SynthesisResult
from app.service.extract import ExtractionError

client = TestClient(app)
KEY = {"X-API-Key": "test-key"}

# The escalating URL and the firecrawl cassette recorded for it: the request body must match
# the recording, so the URL is the one the cassette was recorded against.
_ESCALATING_URL = "https://httpbin.org/html"
_FIRECRAWL_CASSETTE = str(
    Path(__file__).resolve().parent / "cassettes" / "test_fallback_fetch" / "test_firecrawl_http_surface.yaml"
)

_UNITS = [
    ParagraphUnit(type="paragraph", display="p1", spoken="p1"),
    ParagraphUnit(type="paragraph", display="p2", spoken="p2"),
]


def _db_path() -> Path:
    return Path(os.environ["NAGARA_DATA_DIR"]) / "test.db"


def _fetch(sql: str, params: tuple = ()):
    with sqlite3.connect(str(_db_path())) as conn:
        return conn.execute(sql, params).fetchone()


def _create() -> str:
    with (
        patch("app.service.lifecycle.extract_with_fallback", return_value=("Title", _UNITS, "<html></html>")),
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-cost"),
    ):
        return client.post("/items", json={"url": "https://example.test/post"}, headers=KEY).json()["id"]


@pytest.mark.vcr(_FIRECRAWL_CASSETTE)
def test_enqueue_records_a_firecrawl_cost_entry(vcr):
    # The plain fetch is forced to fail so the enqueue escalates and the only recorded request
    # is the firecrawl POST. Everything below the route runs for real, so the CostEntry is
    # written by the lifecycle, priced from Settings.
    with (
        patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")),
        patch("app.config.settings.firecrawl_api_key", "replay-key"),
        patch("app.service.lifecycle.spawn_synthesis", return_value="fc-cost"),
    ):
        item_id = client.post("/items", json={"url": _ESCALATING_URL}, headers=KEY).json()["id"]

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


def test_ready_item_records_a_tts_cost_entry():
    item_id = _create()
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
        client.get(f"/items/{item_id}", headers=KEY)

    row = _fetch(
        "SELECT quantity, unit, dollars, detail FROM cost_entries WHERE item_id = ? AND type = 'tts'",
        (item_id,),
    )
    assert row is not None
    assert row[0] == 6.0
    assert row[1] == "seconds"
    assert row[2] == pytest.approx(6.0 * settings.tts_dollars_per_second)
    assert json.loads(row[3])["duration"] == 6.0
