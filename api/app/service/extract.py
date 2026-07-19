import re

import trafilatura
from markdown_it import MarkdownIt

_FOOTNOTE_GLYPHS = re.compile(r"[↩⇧]")
_NAV_LABELS = {"table of contents", "contents"}

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
_FENCE = re.compile(r"^\s*(```|~~~)")
_BLOCKQUOTE = re.compile(r"^\s*>")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s+")

_CODE_SPAN = re.compile(r"(`+)[^`]*?\1")
_LINK_DEST = re.compile(r"\]\([^)]*\)")
_PLACEHOLDER = re.compile("\x00(\\d+)\x00")

# trafilatura renders an inline <code> whose text contains a newline as a fence glued mid-paragraph
# — the opening fence at the end of a prose line, the content, then a lone closing fence on its own
# line — instead of an inline `code` span. A fenced block can never open mid-line in CommonMark (only
# whitespace may precede an opening fence), so a fence preceded by text on its line is unambiguously
# this artifact. Left in place, its lone closing fence is later misread as a block-opening fence and
# every following code block cascades apart. The `(?<=\S)` lookbehind fires only on the glued
# (mid-line) opener; the `\1` backreference keeps ``` and ~~~ from cross-pairing; the trailing
# `(?=\n|\Z)` requires the closing fence to own its line — the surviving newline is what the
# soft-wrap rejoin turns back into the word boundary after the collapsed span. The content is
# tempered to stop at a blank line: inline code never spans a paragraph break, so an unbalanced
# opener can never reach across one to swallow a genuine block's opening fence as its "close".
_INLINE_FENCE = re.compile(
    r"(?<=\S)[ \t]*(```|~~~)[ \t]*\n((?:(?!\n[ \t]*\n).)*?)\n[ \t]*\1[ \t]*(?=\n|\Z)", re.DOTALL
)

# One per emphasis delimiter trafilatura emits (** for strong, * for emphasis; never _ / __).
# Each matches a delimiter pair whose opener is adjacent to its content — so spaced asterisks
# (`2 * 3`) are never turned into emphasis — capturing content trimmed of a stray space before
# the closer, with the following character looked ahead to decide whether a boundary is needed.
# An unspaced single-`*` run (`2*3*4`) is left as trafilatura emits it: it is a valid but
# ambiguous emphasis pair, and forcing a word-boundary opener to reject it would also stop
# repairing genuine intra-word emphasis — so it stays as-is, like an unbalanced `***`.
_EMPHASIS = [
    (d, re.compile(rf"{re.escape(d)}([^\s{re.escape(d[0])}](?:[^{re.escape(d[0])}]*[^\s{re.escape(d[0])}])?)\s*{re.escape(d)}(?=(.?))"))
    for d in ("**", "*")
]

_md = MarkdownIt("commonmark").enable("table")


class ExtractionError(Exception):
    pass


def extract_article(url: str) -> tuple[str | None, list[str], list[str]]:
    """Fetch a URL and turn it into aligned display/spoken paragraph lists.

    Returns ``(title, display, spoken)`` where ``display[i]`` is the markdown a
    client renders and ``spoken[i]`` is the same unit stripped to clean prose for
    synthesis — equal length, same index by construction. Non-HTML clean-fails.
    """
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

    markdown = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=True,
        favor_precision=True,
        include_comments=False,
    )
    if not markdown:
        raise ExtractionError("no article text extracted")

    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta else None

    display, spoken = paragraphs_from_markdown(markdown, title)
    if not display:
        raise ExtractionError("no paragraphs after extraction")

    return title, display, spoken


def paragraphs_from_markdown(markdown: str, title: str | None) -> tuple[list[str], list[str]]:
    """Segment an extracted markdown document into display units and derive the
    spoken form of each. A unit is dropped from *both* lists when it is edge cruft
    (echoed title, nav label, punctuation-only) or when its spoken form is empty —
    so display and spoken stay index-aligned and no empty text reaches synthesis."""
    title_norm = (title or "").strip().lower()
    display: list[str] = []
    spoken: list[str] = []

    markdown = _repair_inline_fences(markdown)

    for unit in _split_units(markdown):
        unit = _FOOTNOTE_GLYPHS.sub("", unit).strip()
        if not unit or _is_cruft(unit, title_norm):
            continue

        unit = _normalize_display(unit)

        said = _to_spoken(unit)
        if not said:
            continue

        display.append(unit)
        spoken.append(said)

    return display, spoken


def _normalize_display(unit: str) -> str:
    """Repair trafilatura's emphasis-boundary spacing so a client renders the unit as valid
    CommonMark. trafilatura emits a closing `**`/`*` that abuts the next token — either directly
    (`**bold**word`) or with a stray inner space (`**text: **more`) — which fuses words or, when
    it invalidates the emphasis, leaks the literal markers. Trim the stray space and insert the
    boundary the closer needs. Inline code spans, link/image destinations, and fenced code blocks
    pass through untouched — their delimiter characters (`` `**kwargs` ``) are not emphasis."""
    if _FENCE.match(unit):
        return unit

    holes: list[str] = []

    def stash(match: re.Match[str]) -> str:
        holes.append(match.group(0))
        return f"\x00{len(holes) - 1}\x00"

    masked = _LINK_DEST.sub(stash, _CODE_SPAN.sub(stash, unit))

    for delim, pattern in _EMPHASIS:

        def repair(match: re.Match[str], delim: str = delim) -> str:
            pair = f"{delim}{match.group(1)}{delim}"
            following = match.group(2)
            # A word, a link/image start, or a placeholder (a masked code span / link that will
            # be restored right here) would render fused against the closer, so insert a boundary.
            fuses = bool(following) and (following.isalnum() or following in "[(\x00")
            return f"{pair} " if fuses else pair

        masked = pattern.sub(repair, masked)

    return _PLACEHOLDER.sub(lambda m: holes[int(m.group(1))], masked)


def _is_cruft(unit: str, title_norm: str) -> bool:
    """Trim the edge cruft trafilatura leaves — the echoed title, nav labels, and
    punctuation-only artifacts — comparing against the unit's text with any leading
    markdown marker removed, since a `#`/list prefix would otherwise defeat the match."""
    core = _LIST_ITEM.sub("", _HEADING.sub("", unit)).strip()
    low = core.lower()

    if title_norm and low == title_norm:
        return True
    if low in _NAV_LABELS:
        return True
    if not any(c.isalnum() for c in core):
        return True

    return False


def _repair_inline_fences(markdown: str) -> str:
    """Collapse an inline `<code>` the extractor mis-rendered as a mid-paragraph fence back into an
    inline code span, before block boundaries are computed. Only the balanced artifact shape (glued
    opener + a lone closing fence) is repaired; the content is whitespace-collapsed to one line and
    the leading space is restored so the span reads with a word boundary against the preceding word."""
    return _INLINE_FENCE.sub(lambda m: f" `{' '.join(m.group(2).split())}`", markdown)


def _split_units(markdown: str) -> list[str]:
    """Split markdown into display units. The boundary is the blank line — markdown
    output soft-wraps a paragraph across single newlines, so a paragraph block's
    soft-wraps are joined into one unit; a list block is split into per-item units;
    a fenced code block, blockquote, or table block is kept as one raw unit so the
    parser handles its markers instead of them leaking into the spoken text."""
    units: list[str] = []

    for block in _blocks(markdown):
        if _FENCE.match(block):
            units.append(block)
            continue

        lines = block.split("\n")
        if all(_TABLE_ROW.match(ln) for ln in lines if ln.strip()):
            units.append(block)
            continue
        if all(_BLOCKQUOTE.match(ln) for ln in lines if ln.strip()):
            units.append(block)
            continue
        if any(_LIST_ITEM.match(ln) for ln in lines):
            units.extend(_split_list_items(lines))
        else:
            units.append(" ".join(ln.strip() for ln in lines))

    return units


def _blocks(markdown: str) -> list[str]:
    """Group markdown lines into blocks on blank-line boundaries, but keep a fenced
    code block whole — its own internal blank lines must not split it, or the block
    fragments and its closing fence leaks into prose."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush() -> None:
        if any(ln.strip() for ln in current):
            blocks.append("\n".join(current).strip("\n"))
        current.clear()

    for line in markdown.split("\n"):
        if in_fence:
            current.append(line)
            if _FENCE.match(line):  # closing fence
                flush()
                in_fence = False
            continue

        if _FENCE.match(line):  # opening fence
            flush()
            current.append(line)
            in_fence = True
            continue

        if not line.strip():
            flush()
            continue

        current.append(line)

    flush()

    return blocks


def _split_list_items(lines: list[str]) -> list[str]:
    """Each marker line starts an item; a non-marker line is a soft-wrap
    continuation folded into the current item. A nested (indented) sub-item begins
    with its own marker, so it becomes its own unit — the list is flattened."""
    items: list[str] = []

    for line in lines:
        if _LIST_ITEM.match(line):
            items.append(line.strip())
        elif items:
            items[-1] += " " + line.strip()

    return items


def _to_spoken(unit: str) -> str:
    """Render one markdown unit to clean spoken text: emphasis → inner text, link →
    anchor text (URL dropped), heading/list markers dropped, a code block → a short
    placeholder (the interim spoken form for code), a table → header-aware prose."""
    if _FENCE.match(unit):
        return "Code sample."

    if _TABLE_ROW.match(unit.lstrip().split("\n", 1)[0]):
        return _table_to_spoken(unit)

    out: list[str] = []
    boundary = False

    def emit_text(content: str) -> None:
        nonlocal boundary
        if not content:
            return
        # trafilatura drops the space at a run-in emphasis close (`**phrase**word`);
        # restore it only on the close edge — the open edge keeps its space, and
        # flagging it would over-split intra-word emphasis (`super**b**` → "super b").
        if boundary and out and out[-1][-1:].isalnum() and content[:1].isalnum():
            out.append(" ")
        out.append(content)
        boundary = False

    for tok in _md.parse(unit):
        if tok.type != "inline":
            continue
        for child in tok.children or []:
            if child.type in ("text", "code_inline"):
                emit_text(child.content)
            elif child.type in ("softbreak", "hardbreak"):
                out.append(" ")
                boundary = False
            elif child.type.endswith("_close"):
                boundary = True
            elif child.type.endswith("_open"):
                boundary = False

    spoken = "".join(out)

    # Belt-and-suspenders: trafilatura emits CommonMark-invalid run-in bold (a
    # closing `**` preceded by punctuation and followed by a letter, `review.**Agents`)
    # that fails the flanking rule, so the parser leaves the literal markers. Turn any
    # leftover emphasis marker into a space (splitting the fused word/sentence), then tidy.
    spoken = re.sub(r"\*\*|__|\*|`", " ", spoken)
    spoken = re.sub(r"\s+([,.;:!?])", r"\1", spoken)

    return re.sub(r"\s+", " ", spoken).strip()


def _table_to_spoken(table: str) -> str:
    """Linearize a markdown table into header-aware prose ("Col: value, Col: value.")
    so it reads instead of speaking pipe characters."""
    rows: list[list[str]] = []
    cur: list[str] = []

    for tok in _md.parse(table):
        if tok.type == "inline":
            cur.append(tok.content)
        elif tok.type == "tr_close":
            rows.append(cur)
            cur = []

    if len(rows) < 2:
        return " ".join(rows[0]) if rows else ""

    header = rows[0]
    return ". ".join(
        ", ".join(f"{header[i]}: {cell}" for i, cell in enumerate(row) if i < len(header))
        for row in rows[1:]
    ) + "."


def _content_type(response) -> str:
    return next(
        (str(v).lower() for k, v in (response.headers or {}).items() if k.lower() == "content-type"),
        "",
    )
