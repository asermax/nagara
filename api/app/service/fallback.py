from firecrawl import Firecrawl
from starlette.concurrency import run_in_threadpool

from ..schemas.items import Unit
from .extract import ExtractionError, _extract_units_from_html, extract_article

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
    url: str, firecrawl_api_key: str | None
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
            _fetch_and_extract, url, firecrawl_api_key
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


def _fetch_and_extract(url: str, api_key: str) -> tuple[str | None, list[Unit], str]:
    """Scrape via firecrawl in the calling thread and feed rawHtml through the same
    segmentation the plain fetch uses. Any SDK failure — network, auth, rate limit,
    server — is a firecrawl that could not be reached for this item and collapses to
    one error."""
    client = Firecrawl(api_key=api_key)
    # rawHtml feeds the shared trafilatura segmentation; markdown rides along at the same
    # credit as evidence and is not read. proxy="auto" bills 1 when basic suffices and 5
    # on a stealth escalation, while the response reports the mode as "basic"/"stealth"
    # (grepping one term misses the other). max_age is omitted on purpose: the cache bills
    # full price either way and only trades freshness, capped at firecrawl's default.
    try:
        document = client.scrape(url, formats=["rawHtml", "markdown"], proxy="auto")
    except Exception as e:
        raise ExtractionError("fetch: firecrawl unreachable") from e

    raw_html = getattr(document, "raw_html", None)
    if not raw_html:
        return None, [], ""

    try:
        title, units = _extract_units_from_html(raw_html, url)
    except ExtractionError:
        # rawHtml that yields no article is firecrawl producing nothing usable; the
        # orchestrator falls back to whatever the plain path had.
        return None, [], ""

    return title, units, raw_html


def _spoken_words(units: list[Unit]) -> int:
    return sum(len(unit.spoken.split()) for unit in units)
