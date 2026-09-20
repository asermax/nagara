"""The fetch seam: turn a URL into an article's HTML.

A ``Fetcher`` is the capability interface every fetch strategy implements. The fetch the
item pipeline uses is always firecrawl (``FirecrawlFetcher`` here, beside the SDK it
drives so a test patches that library at one place); the plain trafilatura fetch stays
importable in ``extract`` as the pre-service reference. This module carries the shared
abstraction, the value types that cross the seam, and the firecrawl fetcher.

A fetcher is synchronous: the libraries block, and the pipeline bridges the call through
``run_in_threadpool`` at the step, matching the codebase's convention of bridging a sync
library at its call site rather than hiding a thread hop inside every fetcher.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from firecrawl import Firecrawl


class ExtractionError(Exception):
    """A fetch or extraction failure whose message already carries its ``fetch:`` or
    ``extraction:`` prefix, so the pipeline's failure write passes it through as the
    item's error."""


@dataclass(frozen=True)
class FetchedPage:
    """One fetched document: the HTML the extraction service segments, and the URL the
    fetch finally landed on.

    ``url`` is the *final* URL — redirects resolved — because the recipe domain is the
    final host, and consolidation across domains comes from exactly those redirects.
    ``source`` is which fetch produced the page.
    """

    html: str
    url: str
    source: str


@dataclass(frozen=True)
class FirecrawlUsage:
    """What one firecrawl scrape billed, read off the response. Emitted whenever the scrape
    succeeds — even when its extraction is thin and the baseline wins — because the credit is
    spent on the call, not on the winning extraction."""

    credits: int
    destination: str
    proxy: str | None


class Fetcher(Protocol):
    """Turn a URL into a ``FetchedPage``, or raise ``ExtractionError``. Synchronous by contract."""

    def fetch(self, url: str) -> FetchedPage: ...


def _usage_from_document(document: object, url: str) -> FirecrawlUsage:
    # The SDK parses its camelCase response into snake_case metadata (creditsUsed →
    # credits_used). A mock document without metadata reports zero credits and the request
    # URL, which is only ever the no-network unit tests — a real scrape always carries it.
    metadata = getattr(document, "metadata", None)
    return FirecrawlUsage(
        credits=getattr(metadata, "credits_used", None) or 0,
        destination=getattr(metadata, "source_url", None) or url,
        proxy=getattr(metadata, "proxy_used", None),
    )


class FirecrawlFetcher:
    """A firecrawl scrape as the pipeline's fetch. rawHtml is chosen over firecrawl's cleaned
    HTML (byte-identical prose through the same converter, but it keeps the images the
    cleaning drops) and is handed to the extraction service unsegmented; markdown rides
    along at the same credit as evidence, never read. ``proxy="auto"`` bills 1 on a basic
    proxy and 5 on a stealth escalation. Any SDK failure is a firecrawl that could not be
    reached and collapses to one error; the usage callback fires the moment the scrape
    bills, before any empty return."""

    def __init__(self, api_key: str, on_cost: Callable[[FirecrawlUsage], None] | None = None):
        self._api_key = api_key
        self._on_cost = on_cost

    def fetch(self, url: str) -> FetchedPage:
        client = Firecrawl(api_key=self._api_key)
        try:
            document = client.scrape(url, formats=["rawHtml", "markdown"], proxy="auto")
        except Exception as e:
            raise ExtractionError("fetch: firecrawl unreachable") from e

        if self._on_cost is not None:
            self._on_cost(_usage_from_document(document, url))

        raw_html = getattr(document, "raw_html", None)
        if not raw_html:
            raise ExtractionError("fetch: firecrawl returned no HTML")

        metadata = getattr(document, "metadata", None)
        final_url = getattr(metadata, "url", None) or url
        return FetchedPage(html=raw_html, url=final_url, source="firecrawl")
