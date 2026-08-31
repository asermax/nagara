import configparser
import re
from dataclasses import dataclass
from typing import Protocol

import trafilatura
from markdown_it import MarkdownIt
from trafilatura.downloads import DEFAULT_CONFIG as _DEFAULT_CONFIG

from ..schemas.items import CodeUnit, ParagraphUnit, Unit, UnitType
from .fetch import FetchedPage

_FOOTNOTE_GLYPHS = re.compile(r"[↩⇧]")
# A footnote reference marker is only separable from prose while its markup still exists:
# trafilatura renders `<sup><a data-footnote-ref>1</a></sup>` as a bare digit in the sentence,
# and "here to stay 3, I'm a craftsman" is textually the same shape as "step 5, I'm operating".
# So the marker is pruned from the tree, before extraction, by the markup that identifies it.
# Bare `//sup` is excluded: a superscript with no link is an exponent, an ordinal or a
# trademark as often as it is a footnote.
_FOOTNOTE_REF_XPATH = [
    "//sup[a]",
    "//a[@data-footnote-ref]",
    "//sup[@class='reference']",
    "//a[contains(@class, 'footnote-anchor')]",
]
_NAV_LABELS = {"table of contents", "contents"}

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
# CommonMark allows at most three leading spaces before a fence opener; \s* is looser and
# also matches indented literals and traceback carets (``    ~~~^~~``), which then toggle the
# fence state the wrong way and swallow the prose between them and the next fence line.
_FENCE = re.compile(r"^[ ]{0,3}(```|~~~)")
_BLOCKQUOTE = re.compile(r"^\s*>")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s+")

# Inline code spans and link destinations lose the same boundary as emphasis: trafilatura
# discards the whitespace following any inline element, so a closer abuts the next token
# (`None`and, [a](u)or). The following character is captured in a lookahead, not consumed —
# anchoring on a delimiter pair and testing the next char makes a non-matching span's closer
# become the next match's opener, so the gap between two spans is treated as a span and the
# boundary lands inside it. These patterns mask (so the emphasis pass cannot reach into a URL
# or a `**kwargs` span) and repair the trailing boundary in the same step.
_CODE_SPAN = re.compile(r"(`+)[^`]*?\1(?=(?P<next>.?))")
_LINK_DEST = re.compile(r"\]\([^)]*\)(?=(?P<next>.?))")
_PLACEHOLDER = re.compile("\x00(\\d+)\x00")

# CommonMark's inline-HTML tag shape, drawn on markdown-it's own boundary: `<T>`, `<br/>` and
# `<not a tag>` are tags to the parser, while `3 < 4`, `<3` and the autolink `<a@b.com>` are not.
# trafilatura strips every real element, comment, custom tag and inline SVG before it emits
# markdown, so a tag that survives into the extracted text is prose the author wrote as
# `&lt;software&gt;` rather than leaked markup: the words inside it are the article's own.
_TAG_SHAPE = r"</?([A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*?)?)\s*/?>"
# The display escape skips an already-escaped tag, so normalization stays idempotent.
_UNESCAPED_HTML_TAG = re.compile(rf"(?<!\\){_TAG_SHAPE}")
# The spoken strip also takes the escaped form: a table cell is read off the raw inline source,
# where the backslash `_normalize_display` inserted is still sitting in front of the tag.
_SPOKEN_HTML_TAG = re.compile(rf"\\?{_TAG_SHAPE}")

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


@dataclass(frozen=True)
class Extraction:
    """One segmentation: the article title and its typed display units, index-aligned by
    construction. What an ``Extractor`` returns for a ``FetchedPage``."""

    title: str | None
    units: list[Unit]


class Extractor(Protocol):
    """Turn a ``FetchedPage`` into an ``Extraction``, or raise ``ExtractionError``."""

    def extract(self, page: FetchedPage) -> Extraction: ...


class TrafilaturaExtractor:
    """The single ``trafilatura.extract`` + segmentation seam. The plain and firecrawl fetches
    both route their HTML through here, so invariant 1 holds by construction: one markdown
    segmentation is the source of truth for both the spoken and the display form."""

    def extract(self, page: FetchedPage) -> Extraction:
        title, units = _extract_units_from_html(page.html, page.url)
        return Extraction(title=title, units=units)


class PlainFetcher:
    """``trafilatura.fetch_response`` under a browser user agent, with the three pre-extraction
    gates: a non-2xx status, an empty body, and a non-HTML content type each clean-fail with a
    ``fetch:`` reason before any extraction runs. It lives here, beside this module's
    ``trafilatura`` import, so a test patches one library at one place."""

    def fetch(self, url: str) -> FetchedPage:
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

        if response.html is None:
            raise ExtractionError("fetch: could not decode response body")

        return FetchedPage(html=response.html, url=url, source="plain")


def extract_article(url: str) -> tuple[str | None, list[Unit], str]:
    """Fetch a URL and turn it into typed display units.

    Returns ``(title, units, html)`` where each unit carries its provisional type, the
    display markdown a client renders, and the spoken prose synthesized for it — same index
    by construction. The raw HTML is returned alongside so the image selection can probe
    into the same tree the extraction read. A non-2xx response or a non-HTML content type
    clean-fails before any extraction runs.
    """
    page = PlainFetcher().fetch(url)
    extraction = TrafilaturaExtractor().extract(page)
    return extraction.title, extraction.units, page.html


def _extract_units_from_html(html: str, url: str) -> tuple[str | None, list[Unit]]:
    # The single trafilatura.extract + segmentation call site. The plain fetch and the
    # firecrawl fallback both route their HTML through here, so invariant 1 holds by
    # construction: one markdown segmentation produces the spoken and display forms.
    markdown = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=True,
        favor_precision=True,
        include_comments=False,
        prune_xpath=_FOOTNOTE_REF_XPATH,
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


def _fuses(following: str) -> bool:
    """True when the character after an inline code span or link destination would render fused
    against the closer — a word, a link/image `[`, an opening paren, or the `<` of a tagged word
    — so the boundary trafilatura dropped must be restored. A masked placeholder is excluded:
    this runs during masking on raw text, and the emphasis pass separately owns the edge from its
    own closer to a restored span."""
    return bool(following) and (following.isalnum() or following in "[(<")


def _normalize_display(unit: str) -> str:
    """Repair trafilatura's inline-boundary spacing so a client renders the unit as valid
    CommonMark. trafilatura discards the whitespace following any inline element — emphasis, an
    inline code span, or a link destination — so a closer abuts the next token and fuses words
    (`**bold**word`, `code`next, `[a](u)or`), or, when it invalidates the emphasis, leaks the
    literal markers. Each code span and link destination is masked so the emphasis pass cannot
    reach into it, with a boundary inserted against whatever follows; each emphasis pair then has
    any stray space before its closer trimmed and the same boundary test applied. An XML-like
    tagged word the author wrote (`<software>`) is then backslash-escaped, so a renderer shows
    the word instead of reading it as an unknown element. A fenced code block passes through
    untouched — its backticks are not spans, and its angle brackets already render literally."""
    if _FENCE.match(unit):
        return unit

    holes: list[str] = []

    def stash(match: re.Match[str]) -> str:
        holes.append(match.group(0))
        placeholder = f"\x00{len(holes) - 1}\x00"
        following = match.group("next")
        return f"{placeholder} " if _fuses(following) else placeholder

    masked = _LINK_DEST.sub(stash, _CODE_SPAN.sub(stash, unit))

    for delim, pattern in _EMPHASIS:

        def repair(match: re.Match[str], delim: str = delim) -> str:
            pair = f"{delim}{match.group(1)}{delim}"
            following = match.group(2)
            # A word, a link/image start, the `<` of a tagged word, or a placeholder (a masked
            # code span / link restored right here) renders fused against the closer, so insert
            # a boundary. The tag is escaped after this pass, so `<` is still the char seen here.
            fuses = bool(following) and (following.isalnum() or following in "[(<\x00")
            return f"{pair} " if fuses else pair

        masked = pattern.sub(repair, masked)

    masked = _UNESCAPED_HTML_TAG.sub(r"\\\g<0>", masked)

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

    # Belt-and-suspenders: trafilatura emits CommonMark-invalid run-in bold (a
    # closing `**` preceded by punctuation and followed by a letter, `review.**Agents`)
    # that fails the flanking rule, so the parser leaves the literal markers.
    return sanitize_spoken("".join(out))


def sanitize_spoken(text: str) -> str:
    """Turn any leftover markdown emphasis or code marker into a space (splitting the fused
    word or sentence), drop the space a marker left before punctuation, and collapse runs of
    whitespace. The same tail guards two producers: trafilatura's parsed prose, whose invalid
    run-in emphasis leaks a literal marker, and the describer's structured output, which a JSON
    schema cannot forbid a marker from carrying inside its string value. A leaked marker is only
    ever caught by playing the audio, so both paths run through here.

    It also reduces an XML-like tagged word to the words inside it (`<software>` → software),
    escaped or not: escaped is the shape a table cell arrives in, since ``_table_to_spoken``
    reads a cell off the raw inline source."""
    text = _SPOKEN_HTML_TAG.sub(r"\1", text)
    text = re.sub(r"\*\*|__|\*|`", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)

    return re.sub(r"\s+", " ", text).strip()


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
        return sanitize_spoken(" ".join(rows[0])) if rows else ""

    header = rows[0]
    # Cells carry raw inline markup (a `code` span reads its literal backtick), so the
    # linearized table runs through the same sanitize tail every other spoken path does.
    return sanitize_spoken(
        ". ".join(
            ", ".join(f"{header[i]}: {cell}" for i, cell in enumerate(row) if i < len(header))
            for row in rows[1:]
        )
        + "."
    )


def _content_type(response) -> str:
    return next(
        (str(v).lower() for k, v in (response.headers or {}).items() if k.lower() == "content-type"),
        "",
    )
