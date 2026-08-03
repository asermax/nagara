"""Fetch-contract tests for the plain fetch.

These prove the two fixes a module-boundary mock structurally cannot: that the browser
user agent is actually sent and that ``response.status`` is actually read. A ``@patch`` of
``trafilatura.fetch_response`` replaces the function wholesale, so it verifies neither; a
cassette records the request headers and the response status, so both run against the real
``fetch_response``.

Replay-only at record mode ``none`` (CI adds ``--block-network``). Re-record one cassette
locally with ``uv run pytest --record-mode=rewrite tests/test_fetch_contract.py::<name>``,
which needs network but no credentials.
"""
import pytest

from app.service.extract import BROWSER_USER_AGENT, ExtractionError, extract_article


def _header(headers, name):
    low = name.lower()
    return next((v for k, v in headers.items() if k.lower() == low), None)


@pytest.mark.vcr
def test_plain_fetch_sends_a_browser_user_agent(vcr):
    # extract_article runs end to end against a recorded 200 HTML page; the recorded
    # request is what the real fetch sent, so its User-Agent is the browser string, not
    # trafilatura's default "trafilatura/…" agent that some hosts 403.
    title, units = extract_article("https://httpbin.org/html")

    assert title == "Herman Melville - Moby-Dick"
    assert units
    request = vcr.requests[0]
    assert request.method == "GET"
    assert request.uri == "https://httpbin.org/html"
    assert _header(request.headers, "User-Agent") == BROWSER_USER_AGENT


@pytest.mark.vcr
def test_non_2xx_response_raises_a_fetch_error():
    # A recorded 403 is read off response.status and fails honestly with the fetch:
    # prefix before any extraction runs. The status check sits ahead of the body checks,
    # so a non-2xx is caught whether or not its body would have extracted — the real
    # mitchellh.com 403 ships a 33 KB error-page body that would otherwise synthesize.
    # httpbin.org/status/403 is the stable, purpose-built non-2xx source for the cassette.
    with pytest.raises(ExtractionError, match=r"^fetch: HTTP 403"):
        extract_article("https://httpbin.org/status/403")
