import configparser
import re

import trafilatura
from markdown_it import MarkdownIt
from trafilatura.downloads import DEFAULT_CONFIG as _DEFAULT_CONFIG

from ..schemas.items import CodeUnit, ParagraphUnit, Unit, UnitType

_FOOTNOTE_GLYPHS = re.compile(r"[↩⇧]")
_NAV_LABELS = {"table of contents", "contents"}

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
# CommonMark allows at most three leading spaces before a fence opener; \s* is looser and
# also matches indented literals and traceback carets (``    ~~~^~~``), which then toggle the
# fence state the wrong way and swallow the prose between them and the next fence line.
_FENCE = re.compile(r"^[ ]{0,3}(```|~~~)")
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

# A browser user agent reaches hosts that 403 the library's own default agent; the rest of
# the corpus extracts identically either way, so only the agent string moves.
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/145.0.0.0 Safari/537.36"
)

# trafilatura reads MAX_FILE_SIZE, COOKIE and the timeout/redirect limits unconditionally
# from any config that is not its own DEFAULT_CONFIG — a fresh ConfigParser KeyErrors on the
# first fetch — so carry the defaults verbatim and override only the user agent.
_FETCH_CONFIG = configparser.ConfigParser()
_FETCH_CONFIG.read_dict({"DEFAULT": dict(_DEFAULT_CONFIG["DEFAULT"])})
_FETCH_CONFIG.set("DEFAULT", "USER_AGENTS", BROWSER_USER_AGENT)


class ExtractionError(Exception):
    pass


def extract_article(url: str) -> tuple[str | None, list[Unit]]:
    """Fetch a URL and turn it into typed display units.

    Returns ``(title, units)`` where each unit carries its provisional type, the display
    markdown a client renders, and the spoken prose synthesized for it — same index by
    construction. A non-2xx response or a non-HTML content type clean-fails before any
    extraction runs.
    """
    response = trafilatura.fetch_response(
        url, decode=True, with_headers=True, config=_FETCH_CONFIG
    )
    if response is None:
        raise ExtractionError("fetch: no response")
    # A non-2xx is read off the response before the body is interpreted: a 403 error
    # page arrives with a body that would otherwise pass the emptiness check and extract.
    if not 200 <= response.status < 300:
        raise ExtractionError(f"fetch: HTTP {response.status}")
    if not response.data:
        raise ExtractionError("fetch: empty response body")

    content_type = _content_type(response)
    if "html" not in content_type:
        raise ExtractionError(
            f"fetch: unsupported content-type '{content_type or 'unknown'}' — only HTML is fetchable"
        )

    html = response.html
    if html is None:
        raise ExtractionError("fetch: could not decode response body")

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
        raise ExtractionError("extraction: no article text")

    meta = trafilatura.extract_metadata(html)
    title = meta.title if meta else None

    units = units_from_markdown(markdown, title)
    if not units:
        raise ExtractionError("extraction: no paragraphs")

    return title, units


def units_from_markdown(markdown: str, title: str | None) -> list[Unit]:
    """Segment an extracted markdown document into typed display units, each carrying its
    provisional type, its display markdown, and its spoken form. A unit is dropped when it
    is edge cruft (echoed title, nav label, punctuation-only) or when its spoken form is
    empty, so a surviving unit keeps its display, spoken, and (later) timing on one object."""
    title_norm = (title or "").strip().lower()
    units: list[Unit] = []

    markdown = _repair_inline_fences(markdown)

    for raw, unit_type in _split_units(markdown):
        unit = _FOOTNOTE_GLYPHS.sub("", raw).strip()
        if not unit or _is_cruft(unit, title_norm):
            continue

        display = _normalize_display(unit)
        said = _to_spoken(display)
        if not said:
            continue

        if unit_type == "code":
            units.append(CodeUnit(type="code", display=display, spoken=said))
        else:
            units.append(ParagraphUnit(type="paragraph", display=display, spoken=said))

    return units


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


def _split_units(markdown: str) -> list[tuple[str, UnitType]]:
    """Split markdown into (display unit, provisional type) pairs. The boundary is the blank
    line — markdown output soft-wraps a paragraph across single newlines, so a paragraph
    block's soft-wraps are joined into one unit; a list block is split into per-item units;
    a fenced code block, blockquote, or table block is kept as one raw unit so the parser
    handles its markers instead of them leaking into the spoken text. A fence is tagged
    ``code`` and everything else ``paragraph``; a fenced block whose interior is mostly
    sentence-shaped prose is re-classified as ``paragraph`` here (see ``_is_fenced_prose``),
    and later quests refine the type further before it reaches the persisted list."""
    units: list[tuple[str, UnitType]] = []

    for block in _blocks(markdown):
        if _FENCE.match(block):
            interior = _fenced_interior(block)
            if _is_fenced_prose(interior):
                units.append((" ".join(ln.strip() for ln in interior.split("\n")), "paragraph"))
            else:
                units.append((block, "code"))
            continue

        lines = block.split("\n")
        if all(_TABLE_ROW.match(ln) for ln in lines if ln.strip()):
            units.append((block, "paragraph"))
            continue
        if all(_BLOCKQUOTE.match(ln) for ln in lines if ln.strip()):
            units.append((block, "paragraph"))
            continue
        if any(_LIST_ITEM.match(ln) for ln in lines):
            for item in _split_list_items(lines):
                units.append((item, "paragraph"))
        else:
            units.append((" ".join(ln.strip() for ln in lines), "paragraph"))

    return units


# Lines that mark a fenced block as genuine code or transcript output: a Python REPL prompt,
# a shell prompt, or a comment opener. Any one vetoes a prose re-classification.
_CODE_MARKERS = (">>>", "$", "#", "//")
# Terminal punctuation that signals a sentence. `;` and `:` are excluded because they are
# code-typical (a ``def`` header, a slice), so counting them would read code as prose.
_SENTENCE_PUNCT = set(".,!?")
_CODE_PUNCT = set("(){}[]=;:+-*<>|&%^/\\")


def _fenced_interior(block: str) -> str:
    """Drop a fenced block's opening and closing fence lines, leaving its interior."""
    return "\n".join(block.split("\n")[1:-1])


def _is_fenced_prose(interior: str) -> bool:
    """Whether a fenced block's interior is sentence-shaped prose that trafilatura wrapped in
    closed fences — no parser recovers it, CommonMark-faithful or otherwise, so the block is
    re-classified as a paragraph and its fences stripped. Requires no REPL/shell/comment
    marker on any line and most lines reading as a sentence, so a genuine transcript or a
    plain code block stays code."""
    lines = [ln for ln in interior.split("\n") if ln.strip()]
    if not lines or any(ln.lstrip().startswith(_CODE_MARKERS) for ln in lines):
        return False
    prose = sum(_is_prose_line(ln) for ln in lines)
    return prose * 2 > len(lines)


def _is_prose_line(line: str) -> bool:
    """A line reads as a sentence when it is mostly letters rather than code punctuation and
    either carries terminal punctuation or spans at least four words — the shape that separates
    a clause from a statement like ``def f():`` or ``x = [1, 2, 3]``."""
    s = line.strip()
    if " " not in s:
        return False
    if sum(c in _CODE_PUNCT for c in s) / len(s) >= 0.25:
        return False
    return len(s.split()) >= 4 or any(c in _SENTENCE_PUNCT for c in s)


def _blocks(markdown: str) -> list[str]:
    """Group markdown lines into blocks on blank-line boundaries, but keep a fenced
    code block whole — its own internal blank lines must not split it, or the block
    fragments and its closing fence leaks into prose.

    An opener with no closer anywhere after it is refused rather than opened: a genuinely
    unclosed fence runs to EOF, and treating it as one code block hides its prose behind
    the code placeholder. The stray opener line is dropped and its contents segment as
    prose, so no backtick marker reaches the spoken text."""
    lines = markdown.split("\n")
    # The index of the last fence line: an opener at or past it has no closer after it.
    fence_lines = [i for i, ln in enumerate(lines) if _FENCE.match(ln)]
    last_fence = fence_lines[-1] if fence_lines else -1

    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush() -> None:
        if any(ln.strip() for ln in current):
            blocks.append("\n".join(current).strip("\n"))
        current.clear()

    for i, line in enumerate(lines):
        if in_fence:
            current.append(line)
            if _FENCE.match(line):  # closing fence
                flush()
                in_fence = False
            continue

        if _FENCE.match(line):  # opening fence
            if i == last_fence:
                # no closer follows: drop the stray opener and let its contents segment as prose
                continue
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
