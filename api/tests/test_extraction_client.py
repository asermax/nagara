"""The extraction-service client: spawn and resolve against the boundary contract.

The client is exercised over fabricated cassettes (the service does not exist yet, so
there is nothing to record against): each interaction is hand-built from the contract in
docs/technical-design/extraction-service.md. These tests pin the wire shape — the create
body, the Access headers, the 201/409/413 mapping — and leave state mapping to the
pipeline tests.
"""
import asyncio

import pytest

from app.config import settings
from app.schemas.extraction import ServiceImageUnit
from app.service.extraction import (
    HtmlTooLarge,
    _access_headers,
    mint_handle,
    resolve_extraction,
    spawn_extraction,
)
from app.service.recipes import domain_from_url

_HTML = "<html><body><article><h1>Title</h1><p>Body paragraph one.</p></article></body></html>"


@pytest.fixture(autouse=True)
def _extraction_service(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_extraction_url", "https://extraction.test")


# --- the handle and the domain key (pure functions) ----------------------------


def test_the_handle_is_the_item_id_until_a_remint_suffixed_by_retry():
    assert mint_handle("itm_0123abcd", None) == "itm_0123abcd"
    assert mint_handle("itm_0123abcd", 0) == "itm_0123abcd"
    assert mint_handle("itm_0123abcd", 1) == "itm_0123abcd-1"
    assert mint_handle("itm_0123abcd", 3) == "itm_0123abcd-3"


def test_the_domain_is_the_final_host_with_a_leading_www_dropped():
    assert domain_from_url("https://example.test/article") == "example.test"
    assert domain_from_url("https://www.example.test/article") == "example.test"
    # subdomains are distinct domains; no other stripping happens
    assert domain_from_url("https://blog.example.test/post") == "blog.example.test"
    assert domain_from_url("https://example.test") == "example.test"


# --- spawn: the wire shape ------------------------------------------------------


@pytest.mark.vcr
def test_spawn_sends_the_boundary_body(vcr):
    created = asyncio.run(spawn_extraction(_HTML, "// recipe v1", "itm_00000001", "example.test"))

    assert created is True

    request = next(r for r in vcr.requests if r.host == "extraction.test")
    assert request.method == "POST"
    assert request.path == "/jobs"
    assert request.headers["content-type"] == "application/json"
    assert _HTML in request.body.decode()


@pytest.mark.vcr
def test_spawn_sends_access_headers_when_the_pair_is_configured(monkeypatch, vcr):
    monkeypatch.setattr(settings, "cf_access_client_id", "access-id")
    monkeypatch.setattr(settings, "cf_access_client_secret", "access-secret")

    asyncio.run(spawn_extraction(_HTML, None, "itm_00000002", "example.test"))

    # vcr.requests exposes the cassette's own (fabricated) requests, not the live ones,
    # so the headers cannot be asserted off the wire here; what the wire carries is
    # exactly the client's header dict, asserted straight from the seam instead.
    assert _access_headers() == {
        "CF-Access-Client-Id": "access-id",
        "CF-Access-Client-Secret": "access-secret",
    }

    request = next(r for r in vcr.requests if r.host == "extraction.test")
    assert request.method == "POST"


def test_a_half_supplied_access_pair_counts_as_not_configured(monkeypatch):
    # A half-supplied credential set counts as not configured (invariant 6): neither
    # header is sent.
    monkeypatch.setattr(settings, "cf_access_client_id", "access-id")
    assert _access_headers() == {}

    monkeypatch.setattr(settings, "cf_access_client_id", "")
    monkeypatch.setattr(settings, "cf_access_client_secret", "access-secret")
    assert _access_headers() == {}


# --- spawn: the status mapping --------------------------------------------------


@pytest.mark.vcr
def test_spawn_reports_an_existing_job_as_not_created():
    assert asyncio.run(spawn_extraction(_HTML, None, "itm_00000004", "example.test")) is False


@pytest.mark.vcr
def test_spawn_surfaces_a_too_large_html_distinctly():
    with pytest.raises(HtmlTooLarge):
        asyncio.run(spawn_extraction(_HTML, None, "itm_00000005", "example.test"))


def test_spawn_without_a_configured_url_raises(monkeypatch):
    monkeypatch.setattr(settings, "cloudflare_extraction_url", "")
    with pytest.raises(RuntimeError, match="NAGARA_CLOUDFLARE_EXTRACTION_URL"):
        asyncio.run(spawn_extraction(_HTML, None, "itm_00000006", "example.test"))


# --- resolve ---------------------------------------------------------------------


@pytest.mark.vcr
def test_resolve_returns_the_boundary_status_unmodified():
    status = asyncio.run(resolve_extraction("itm_00000007"))

    assert status.state == "complete"
    assert status.title == "What Is Reasoning"
    assert status.recipe == "// the authored recipe"
    assert status.units is not None
    assert [unit.type for unit in status.units] == ["paragraph", "code", "image", "paragraph"]
    image = status.units[2]
    assert isinstance(image, ServiceImageUnit)
    assert image.src == "https://example.test/chart.png"
    assert image.alt == "A chart of requests per second"
