from collections.abc import Callable

from firecrawl import Firecrawl
from starlette.concurrency import run_in_threadpool

from ..schemas.items import Unit
from .extract import ExtractionError, TrafilaturaExtractor, extract_article
from .fetch import FetchedPage, FirecrawlUsage


class FirecrawlFetcher:
    """A firecrawl scrape as a fallback fetch. rawHtml is chosen over firecrawl's cleaned HTML
    (byte-identical prose through trafilatura, but it keeps the images the cleaning drops) and
    feeds the same ``TrafilaturaExtractor`` the plain fetch does; markdown rides along at the
    same credit as evidence, never read. ``proxy="auto"`` bills 1 on a basic proxy and 5 on a
    stealth escalation. Any SDK failure is a firecrawl that could not be reached and collapses
    to one error; the usage callback fires the moment the scrape bills, before any empty return.

    It lives here, beside this module's ``Firecrawl`` import, so a test patches the SDK at one
    place.
    """

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

        return FetchedPage(html=raw_html, url=url, source="firecrawl")


# The corpus canyon: the broken X extraction is 37 spoken words and the smallest
# legitimate article is 1,002, so 250 sits inside a 27x gap and an item cannot flap
# between escalating and not. The floor never fails an item on its own — it only buys
# a second opinion, and on the no-baseline path it does not apply at all.
_FIRECRAWL_WORD_FLOOR = 250

# The content-type gate is a clean failure firecrawl cannot improve on, so it is the one
# ExtractionError that never escalates. Matched on its prefix because every phase prefix
# here is already treated as a stable contract by the tests in test_fetch_contract.
_CONTENT_TYPE_GATE = "fetch: unsupported content-type"


async def extract_with_fallback(
    url: str,
    firecrawl_api_key: str | None,
    on_firecrawl_cost: Callable[[FirecrawlUsage], None] | None = None,
) -> tuple[str | None, list[Unit], str]:
    """Plain fetch first, firecrawl as a fallback fetch when the result is absent or thin.

    Returns ``(title, units, html)`` — the HTML is whichever document produced the winning
    extraction, so image selection runs on the tree the units came from.

    Escalation is a second opinion, never a verdict: no trigger fails an item on its own.
    The content-type gate is the one exception — firecrawl will not turn a PDF into HTML,
    so it re-raises unchanged. Everywhere else (a non-2xx, any other fetch or extraction
    failure, or fewer than 250 spoken words) buys exactly one firecrawl fetch, and more
    spoken words wins between the two extractions. With no key configured the path
    degrades to the plain fetch: a failed baseline re-raises, a thin baseline is returned
    as-is, and the floor never fails anything.
    """
    baseline_title, baseline_units, baseline_html, baseline_error = await _baseline(url)

    if baseline_error is not None and str(baseline_error).startswith(_CONTENT_TYPE_GATE):
        raise baseline_error

    if baseline_error is None and _spoken_words(baseline_units) >= _FIRECRAWL_WORD_FLOOR:
        return baseline_title, baseline_units, baseline_html

    if not firecrawl_api_key:
        if baseline_error is not None:
            raise baseline_error
        return baseline_title, baseline_units, baseline_html

    try:
        fc_title, fc_units, fc_html = await run_in_threadpool(
            _fetch_and_extract, url, firecrawl_api_key, on_firecrawl_cost
        )
    except ExtractionError:
        # firecrawl unreachable: a failed baseline has nothing to fall back on, so the
        # item fails with the firecrawl-unreachable error; a successful but thin baseline
        # is kept as-is.
        if baseline_error is not None:
            raise
        return baseline_title, baseline_units, baseline_html

    if _spoken_words(fc_units) > _spoken_words(baseline_units):
        return fc_title, fc_units, fc_html

    if baseline_units:
        return baseline_title, baseline_units, baseline_html

    # No baseline (it raised) and firecrawl produced nothing usable either.
    raise baseline_error if baseline_error is not None else ExtractionError("extraction: no article text")


async def _baseline(
    url: str,
) -> tuple[str | None, list[Unit], str, ExtractionError | None]:
    try:
        title, units, html = await run_in_threadpool(extract_article, url)
    except ExtractionError as e:
        return None, [], "", e
    return title, units, html, None


def _fetch_and_extract(
    url: str,
    api_key: str,
    on_cost: Callable[[FirecrawlUsage], None] | None = None,
) -> tuple[str | None, list[Unit], str]:
    """Fetch via ``FirecrawlFetcher`` and feed its rawHtml through the same
    ``TrafilaturaExtractor`` the plain fetch uses. A firecrawl that could not be reached
    raises; one that returned no HTML, or HTML with no article in it, is firecrawl producing
    nothing usable and collapses to an empty result the orchestrator falls back from."""
    try:
        page = FirecrawlFetcher(api_key, on_cost).fetch(url)
    except ExtractionError as e:
        if "unreachable" in str(e):
            raise
        return None, [], ""

    try:
        extraction = TrafilaturaExtractor().extract(page)
    except ExtractionError:
        return None, [], ""

    return extraction.title, extraction.units, page.html


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


def _spoken_words(units: list[Unit]) -> int:
    return sum(len(unit.spoken.split()) for unit in units)
