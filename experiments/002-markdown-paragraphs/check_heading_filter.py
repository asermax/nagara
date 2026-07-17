"""Does production's content-cleanup still work on markdown units?

Production `api/app/service/extract.py::_clean_paragraphs` drops echoed title, nav labels
(Table of Contents), footnote glyphs, and punctuation-only lines — by EXACT string match.
Under markdown mode those lines now carry `#`/`##` prefixes. This replays production's
filter (as reference, not imported) against the markdown display units to see what still
fires and what a markdown-aware variant would catch instead.

Usage: uv run python check_heading_filter.py
"""

import re
from pathlib import Path

import trafilatura

from pipeline import pipeline

# --- verbatim replica of production _clean_paragraphs logic (reference, not imported) ---
_FOOTNOTE_GLYPHS = re.compile(r"[↩⇧]")
_NAV_LABELS = {"table of contents", "contents"}


def prod_drop(para: str, title_norm: str) -> str | None:
    """Returns the drop-reason if production would drop this line, else None."""
    para = _FOOTNOTE_GLYPHS.sub("", para).strip()
    if not para:
        return "empty"
    low = para.lower()
    if title_norm and low == title_norm:
        return "title-echo"
    if low in _NAV_LABELS:
        return "nav-label"
    if not any(c.isalnum() for c in para):
        return "punct-only"
    return None


# markdown-aware normalisation: strip a leading heading / list marker before comparing
_MARKER = re.compile(r"^\s*(#{1,6}\s+|[-*+]\s+|\d+\.\s+)")


def md_aware_drop(para: str, title_norm: str) -> str | None:
    return prod_drop(_MARKER.sub("", para), title_norm)


def main() -> None:
    html = (Path(__file__).parent / "fixtures" / "my-ai-adoption-journey.html").read_text(encoding="utf-8")
    meta = trafilatura.extract_metadata(html)
    title_norm = (meta.title if meta else "").strip().lower()
    print(f"title: {title_norm!r}\n")

    display, _, _ = pipeline(html)

    for label, fn in (("PRODUCTION filter (as-is)", prod_drop), ("MARKDOWN-AWARE filter", md_aware_drop)):
        dropped = [(u, fn(u, title_norm)) for u in display if fn(u, title_norm)]
        print(f"=== {label}: would drop {len(dropped)} unit(s) ===")
        for u, why in dropped:
            print(f"   [{why}] {u[:70]!r}")
        print()

    # spotlight the two we care about
    for probe in ("# My AI Adoption Journey", "## Table of Contents"):
        got = next((u for u in display if u == probe), None)
        if got:
            print(f"{probe!r}: prod={prod_drop(got, title_norm)} | md-aware={md_aware_drop(got, title_norm)}")


if __name__ == "__main__":
    main()
