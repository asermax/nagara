"""Tests for the firecrawl fallback fetch.

The escalation trigger is protocol facts — a non-2xx, any ``ExtractionError`` save the
content-type gate, or a thin baseline — so most of these tests drive the orchestrator
with the baseline and the firecrawl fetch patched. No network on either side, and
more-spoken-words-wins is a pure function of two extractions.

The one recorded cassette proves the firecrawl HTTP surface: the request body and the
response parsed through the same segmentation the plain fetch uses. It asserts the code
path and the response schema, never a unit count — the measured 5x non-determinism only
bites a re-record, never a replay.

Replay-only at record mode ``none`` (CI adds ``--block-network``). Re-record locally with
``uv run pytest --record-mode=rewrite tests/test_fallback_fetch.py::test_firecrawl_http_surface``,
which needs the firecrawl key in ``api/.env``.
"""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
from app.schemas.items import ParagraphUnit
from app.service.extract import ExtractionError
from app.service.fallback import extract_with_fallback

_KEY = "test-key"


def _para(n_words: int) -> ParagraphUnit:
    return ParagraphUnit(type="paragraph", display="x", spoken=" ".join(["word"] * n_words))


def _units(n_words: int) -> list[ParagraphUnit]:
    # n_words <= 0 is an empty extraction (no surviving unit), the shape a failed
    # segmentation or a firecrawl that yields nothing produces.
    return [_para(n_words)] if n_words > 0 else []


def _words(units: list) -> int:
    return sum(len(u.spoken.split()) for u in units)


def _run(url: str = "https://example.com/article", key: str | None = _KEY):
    return asyncio.run(extract_with_fallback(url, key))


# --- baseline above the floor: no escalation ----------------------------------


def test_baseline_above_floor_is_returned_without_calling_firecrawl():
    with patch("app.service.fallback.extract_article") as baseline, patch(
        "app.service.fallback._fetch_and_extract"
    ) as fc:
        baseline.return_value = ("Title", _units(300))
        title, units = _run()

    assert title == "Title"
    assert _words(units) == 300
    fc.assert_not_called()


# --- the escalation triggers (protocol facts) ---------------------------------


@pytest.mark.parametrize(
    "error",
    [
        ExtractionError("fetch: no response"),
        ExtractionError("fetch: HTTP 403"),
        ExtractionError("fetch: empty response body"),
        ExtractionError("fetch: could not decode response body"),
        ExtractionError("extraction: no article text"),
        ExtractionError("extraction: no paragraphs"),
    ],
)
def test_any_extraction_error_except_content_type_escalates_to_firecrawl(error):
    with patch("app.service.fallback.extract_article", side_effect=error), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(400))
    ) as fc:
        title, units = _run()

    fc.assert_called_once()
    assert title == "FC"
    assert _words(units) == 400


def test_thin_baseline_escalates_to_firecrawl():
    with patch("app.service.fallback.extract_article", return_value=("Thin", _units(100))), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(400))
    ) as fc:
        title, units = _run()

    fc.assert_called_once()
    assert title == "FC"


# --- the content-type gate does NOT escalate ----------------------------------


def test_content_type_gate_does_not_escalate():
    # A PDF is a clean failure firecrawl cannot turn into HTML, so it re-raises unchanged
    # and firecrawl is never reached.
    err = ExtractionError(
        "fetch: unsupported content-type 'application/pdf' — only HTML is fetchable"
    )
    with patch("app.service.fallback.extract_article", side_effect=err), patch(
        "app.service.fallback._fetch_and_extract"
    ) as fc:
        with pytest.raises(ExtractionError, match="unsupported content-type"):
            _run()

    fc.assert_not_called()


# --- more spoken words wins ---------------------------------------------------


def test_firecrawl_with_more_words_wins():
    with patch("app.service.fallback.extract_article", return_value=("Plain", _units(100))), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(500))
    ):
        title, units = _run()

    assert title == "FC"
    assert _words(units) == 500


def test_baseline_kept_when_firecrawl_has_fewer_words():
    # The baseline is thin (100 < 250, so it escalates), firecrawl is thinner still.
    with patch("app.service.fallback.extract_article", return_value=("Plain", _units(100))), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(50))
    ):
        title, units = _run()

    assert title == "Plain"
    assert _words(units) == 100


def test_a_tie_keeps_the_baseline():
    # The comparison is strict greater-than, so equal words keep the plain extraction.
    with patch("app.service.fallback.extract_article", return_value=("Plain", _units(100))), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(100))
    ):
        title, _ = _run()

    assert title == "Plain"


# --- no key configured: degrade to the plain fetch ----------------------------


def test_no_key_failed_baseline_reraises_the_baseline_error():
    with patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")), patch(
        "app.service.fallback._fetch_and_extract"
    ) as fc:
        with pytest.raises(ExtractionError, match="HTTP 403"):
            _run(key=None)

    fc.assert_not_called()


def test_no_key_thin_baseline_is_returned_as_is():
    # The floor never fails an item on its own: a thin baseline with no fallback is kept.
    with patch("app.service.fallback.extract_article", return_value=("Thin", _units(10))), patch(
        "app.service.fallback._fetch_and_extract"
    ) as fc:
        title, units = _run(key=None)

    assert title == "Thin"
    assert _words(units) == 10
    fc.assert_not_called()


# --- the no-baseline path accepts whatever firecrawl returns -------------------


def test_no_baseline_path_accepts_a_thin_firecrawl_result():
    # No floor applies on the no-baseline path: firecrawl's 20 words are taken as-is.
    with patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")), patch(
        "app.service.fallback._fetch_and_extract", return_value=("FC", _units(20))
    ):
        title, units = _run()

    assert title == "FC"
    assert _words(units) == 20


def test_no_baseline_and_empty_firecrawl_reraises_the_baseline_error():
    # Firecrawl produced nothing usable and there is no baseline, so the item fails with
    # the original baseline error rather than a silent empty synthesis.
    with patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")), patch(
        "app.service.fallback._fetch_and_extract", return_value=(None, [])
    ):
        with pytest.raises(ExtractionError, match="HTTP 403"):
            _run()


# --- firecrawl unreachable ----------------------------------------------------


def test_firecrawl_unreachable_with_failed_baseline_fails_the_item():
    with patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")), patch(
        "app.service.fallback._fetch_and_extract",
        side_effect=ExtractionError("fetch: firecrawl unreachable"),
    ):
        with pytest.raises(ExtractionError, match=r"^fetch: firecrawl unreachable"):
            _run()


def test_firecrawl_unreachable_with_thin_baseline_keeps_the_baseline():
    with patch("app.service.fallback.extract_article", return_value=("Thin", _units(100))), patch(
        "app.service.fallback._fetch_and_extract",
        side_effect=ExtractionError("fetch: firecrawl unreachable"),
    ):
        title, units = _run()

    assert title == "Thin"
    assert _words(units) == 100


# --- the firecrawl call parameters (no network) -------------------------------


def test_firecrawl_is_called_with_auto_proxy_and_raw_html_format():
    # The SDK is patched, so this verifies what we pass it with no network and no credit.
    # proxy="auto" bills 1 when basic suffices and 5 only on a stealth escalation;
    # maxAge is omitted because the cache bills full price either way and only costs
    # freshness (capped at firecrawl's 2-day default).
    document = SimpleNamespace(raw_html="<html><body><p>x</p></body></html>")
    with patch("app.service.fallback.extract_article", return_value=("Thin", _units(1))), patch(
        "app.service.fallback.Firecrawl"
    ) as fc_client:
        fc_client.return_value.scrape.return_value = document
        _run(url="https://guarded.example.com/x")

    fc_client.assert_called_once_with(api_key=_KEY)
    _args, kwargs = fc_client.return_value.scrape.call_args
    assert kwargs["formats"] == ["rawHtml", "markdown"]
    assert kwargs["proxy"] == "auto"
    assert "max_age" not in kwargs


def test_firecrawl_passes_the_key_from_settings_explicitly():
    # The key is passed as an api_key argument, never left to the SDK's ambient
    # FIRECRAWL_API_KEY lookup, whose name skips this project's NAGARA_ prefix.
    document = SimpleNamespace(raw_html="<html><body><p>x</p></body></html>")
    with patch("app.service.fallback.extract_article", return_value=("Thin", _units(1))), patch(
        "app.service.fallback.Firecrawl"
    ) as fc_client:
        fc_client.return_value.scrape.return_value = document
        _run(url="https://guarded.example.com/x", key="explicit-from-settings")

    fc_client.assert_called_once_with(api_key="explicit-from-settings")


# --- the firecrawl HTTP surface (one recorded cassette) -----------------------

_FIRECRAWL_URL = "https://httpbin.org/html"


@pytest.mark.vcr
def test_firecrawl_http_surface(vcr):
    # The no-baseline path: the baseline is forced to fail, so the only recorded request
    # is the firecrawl POST. rawHtml feeds the same segmentation the plain fetch uses, so
    # this exercises the shared call site end to end against a recorded response.
    # The key must be truthy or the orchestrator degrades to the plain fetch and never
    # reaches the cassette. It is read from settings so a re-record uses the real one, and
    # falls back to a placeholder because replay never compares it: matching is on
    # method/scheme/host/port/path/query/body, and conftest scrubs `authorization` before
    # anything is written. Without the fallback this test passes only where `api/.env`
    # exists, which is not CI.
    with patch("app.service.fallback.extract_article", side_effect=ExtractionError("fetch: HTTP 403")):
        title, units = asyncio.run(
            extract_with_fallback(_FIRECRAWL_URL, settings.firecrawl_api_key or "replay-key")
        )

    request = next(r for r in vcr.requests if r.host == "api.firecrawl.dev")
    assert request.method == "POST"
    assert request.path == "/v2/scrape"

    body = json.loads(request.body)
    assert body["url"] == _FIRECRAWL_URL
    assert body["formats"] == ["rawHtml", "markdown"]
    assert body["proxy"] == "auto"
    # The SDK serializes a non-zero maxAge default even though max_age is never passed
    # (the mock test above proves that). Asserting it is not forced to 0 documents the
    # quest's reasoning: suppressing the cache bills full price either way and only
    # costs freshness, and maxAge: 0 is more likely to fail on a guarded page.
    assert body.get("maxAge") != 0

    # The no-baseline path accepts whatever comes back: assert the path completed and each
    # surviving unit is typed, never a count (the 5x spread only bites a re-record).
    assert isinstance(units, list)
    assert all(u.type in ("paragraph", "code", "image") for u in units)
