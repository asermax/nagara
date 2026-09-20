"""Tests for the firecrawl fetcher: the pipeline's one fetch.

The fetcher is what the source step hands the extraction service, so its contract is
the rawHtml shape, the scrape parameters, the usage metering, and the final URL the
domain derives from. No network except the one recorded cassette, which asserts the
HTTP surface end to end.

Replay-only at record mode ``none`` (CI adds ``--block-network``). Re-record locally with
``uv run pytest --record-mode=rewrite tests/test_firecrawl_fetch.py::test_firecrawl_http_surface``,
which needs the firecrawl key in ``api/.env``.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
from app.service.fetch import ExtractionError, FirecrawlFetcher, FirecrawlUsage

_KEY = "test-key"


def _document(raw_html: str = "<html><body><p>x</p></body></html>", **metadata) -> SimpleNamespace:
    return SimpleNamespace(raw_html=raw_html, metadata=SimpleNamespace(**metadata) if metadata else None)


# --- the page it returns --------------------------------------------------------


def test_fetch_returns_the_raw_html_page():
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document()
        page = FirecrawlFetcher(_KEY).fetch("https://example.com/article")

    assert page.html == "<html><body><p>x</p></body></html>"
    assert page.source == "firecrawl"


def test_fetch_carries_the_final_url_from_metadata():
    # The domain is derived from the host the fetch landed on — redirects resolved — so
    # the metadata's url (firecrawl's final) is what the page carries; the requested URL
    # is only the fallback when metadata omits it.
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document(url="https://www.final.example.com/article")
        page = FirecrawlFetcher(_KEY).fetch("https://short.example.com/redirect")

    assert page.url == "https://www.final.example.com/article"


def test_fetch_falls_back_to_the_requested_url_without_metadata():
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document()
        page = FirecrawlFetcher(_KEY).fetch("https://example.com/article")

    assert page.url == "https://example.com/article"


# --- failure and emptiness ------------------------------------------------------


def test_sdk_failure_collapses_to_firecrawl_unreachable():
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.side_effect = RuntimeError("dns gone")
        with pytest.raises(ExtractionError, match=r"^fetch: firecrawl unreachable"):
            FirecrawlFetcher(_KEY).fetch("https://example.com/article")


def test_empty_raw_html_is_a_fetch_error():
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document(raw_html="")
        with pytest.raises(ExtractionError, match="returned no HTML"):
            FirecrawlFetcher(_KEY).fetch("https://example.com/article")


# --- usage metering -------------------------------------------------------------


def test_usage_fires_the_moment_the_scrape_bills():
    # The callback fires before any empty-rawHtml return, so a scrape that bills and then
    # yields nothing is still metered — the credit is spent on the call.
    usage: list[FirecrawlUsage] = []
    document = _document(raw_html="", credits_used=5, source_url="https://example.com/article", proxy_used="stealth")
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = document
        with pytest.raises(ExtractionError, match="returned no HTML"):
            FirecrawlFetcher(_KEY, usage.append).fetch("https://example.com/article")

    assert usage == [FirecrawlUsage(credits=5, destination="https://example.com/article", proxy="stealth")]


def test_a_document_without_metadata_reports_zero_credits():
    # The no-network mock shape: zero credits and the request URL as destination, so
    # metering never crashes on a metadata-less document.
    usage: list[FirecrawlUsage] = []
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document()
        FirecrawlFetcher(_KEY, usage.append).fetch("https://example.com/article")

    assert usage == [FirecrawlUsage(credits=0, destination="https://example.com/article", proxy=None)]


# --- the scrape parameters (no network) -----------------------------------------


def test_firecrawl_is_called_with_auto_proxy_and_raw_html_format():
    # proxy="auto" bills 1 when basic suffices and 5 only on a stealth escalation;
    # maxAge is omitted because the cache bills full price either way and only costs
    # freshness (capped at firecrawl's 2-day default).
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document()
        FirecrawlFetcher(_KEY).fetch("https://guarded.example.com/x")

    fc_client.assert_called_once_with(api_key=_KEY)
    _args, kwargs = fc_client.return_value.scrape.call_args
    assert kwargs["formats"] == ["rawHtml", "markdown"]
    assert kwargs["proxy"] == "auto"
    assert "max_age" not in kwargs


def test_firecrawl_passes_the_key_from_settings_explicitly():
    # The key is passed as an api_key argument, never left to the SDK's ambient
    # FIRECRAWL_API_KEY lookup, whose name skips this project's NAGARA_ prefix.
    with patch("app.service.fetch.Firecrawl") as fc_client:
        fc_client.return_value.scrape.return_value = _document()
        FirecrawlFetcher("explicit-from-settings").fetch("https://guarded.example.com/x")

    fc_client.assert_called_once_with(api_key="explicit-from-settings")


# --- the firecrawl HTTP surface (one recorded cassette) -------------------------

_FIRECRAWL_URL = "https://httpbin.org/html"


@pytest.mark.vcr
def test_firecrawl_http_surface(vcr):
    # rawHtml is what crosses to the extraction service, so this exercises the fetch
    # end to end against a recorded response. The key must be truthy or the SDK refuses
    # to run. It is read from settings so a re-record uses the real one, and falls back
    # to a placeholder because replay never compares it: matching is on
    # method/scheme/host/port/path/query/body, and conftest scrubs `authorization`
    # before anything is written.
    page = FirecrawlFetcher(settings.firecrawl_api_key or "replay-key").fetch(_FIRECRAWL_URL)

    request = next(r for r in vcr.requests if r.host == "api.firecrawl.dev")
    assert request.method == "POST"
    assert request.path == "/v2/scrape"

    assert "Moby-Dick" in page.html
    assert page.url == _FIRECRAWL_URL  # the recorded metadata's final url
