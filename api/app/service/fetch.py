"""The fetch seam: turn a URL into an article's HTML.

A ``Fetcher`` is the capability interface every fetch strategy implements — the plain
trafilatura fetch (``PlainFetcher`` in ``extract``) and the firecrawl fallback fetch
(``FirecrawlFetcher`` in ``fallback``). Each concrete fetcher lives beside the library it
drives, so a test can patch that library at its own module; this module carries only the
shared abstraction and the value types that cross the seam.

A fetcher is synchronous: the libraries block, and the pipeline bridges the call through
``run_in_threadpool`` at the step, matching the codebase's convention of bridging a sync
library at its call site rather than hiding a thread hop inside every fetcher.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FetchedPage:
    """One fetched document: the HTML an ``Extractor`` segments, and which fetch produced it.

    ``source`` is ``"plain"`` or ``"firecrawl"`` — the winning fetch, so a later step can tell
    which path an item came down without re-deriving it.
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
