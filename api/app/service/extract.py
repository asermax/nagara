import re

import trafilatura

_FOOTNOTE_GLYPHS = re.compile(r"[↩⇧]")
_NAV_LABELS = {"table of contents", "contents"}


class ExtractionError(Exception):
    pass


def _clean_paragraphs(paragraphs: list[str], title: str | None) -> list[str]:
    """Trim the edge cruft trafilatura leaves: the echoed title, nav labels, footnote
    glyphs, and punctuation-only artifacts. Article body paragraphs pass through."""
    title_norm = (title or "").strip().lower()
    cleaned = []

    for para in paragraphs:
        para = _FOOTNOTE_GLYPHS.sub("", para).strip()
        if not para:
            continue

        low = para.lower()
        if title_norm and low == title_norm:  # echoed title
            continue
        if low in _NAV_LABELS:  # nav label
            continue
        if not any(c.isalnum() for c in para):  # lone dashes/bullets/rules
            continue

        cleaned.append(para)

    return cleaned


def _content_type(response) -> str:
    return next(
        (str(v).lower() for k, v in (response.headers or {}).items() if k.lower() == "content-type"),
        "",
    )


def extract_article(url: str) -> tuple[str | None, list[str]]:
    """Fetch a URL and split it into clean paragraphs. Non-HTML clean-fails."""
    response = trafilatura.fetch_response(url, decode=True, with_headers=True)
    if response is None or not response.data:
        raise ExtractionError("fetch failed or empty response")

    content_type = _content_type(response)
    if "html" not in content_type:
        raise ExtractionError(
            f"unsupported content-type '{content_type or 'unknown'}' — only HTML is fetchable"
        )

    html = response.html
    if html is None:
        raise ExtractionError("could not decode response body")

    text = trafilatura.extract(
        html, url=url, favor_precision=True, include_comments=False, include_tables=False
    )
    if not text:
        raise ExtractionError("no article text extracted")

    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta else None

    paragraphs = _clean_paragraphs([p.strip() for p in text.split("\n") if p.strip()], title)
    if not paragraphs:
        raise ExtractionError("no paragraphs after extraction")

    return title, paragraphs
