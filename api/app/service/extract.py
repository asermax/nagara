import re

from markdown_it import MarkdownIt

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
_FENCE = re.compile(r"^[ ]{0,3}(```|~~~)")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s+")

# CommonMark's inline-HTML tag shape, drawn on markdown-it's own boundary: `<T>`, `<br/>` and
# `<not a tag>` are tags to the parser, while `3 < 4`, `<3` and the autolink `<a@b.com>` are not.
# A tag still present in a unit's markdown is prose the author escaped rather than leaked markup:
# the words inside it are the article's own.
_TAG_SHAPE = r"</?([A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*?)?)\s*/?>"
# The spoken strip also takes the escaped form: a table cell is read off the raw inline source,
# where the backslash escaping the tag in the display is still sitting in front of it.
_SPOKEN_HTML_TAG = re.compile(rf"\\?{_TAG_SHAPE}")

_md = MarkdownIt("commonmark").enable("table")


def is_cruft(text: str, title_norm: str) -> bool:
    """True when the text echoes the article title or carries no letter or digit, comparing
    against the text with any leading markdown marker removed, since a `#`/list prefix would
    otherwise defeat the match."""
    core = _LIST_ITEM.sub("", _HEADING.sub("", text)).strip()

    if title_norm and core.lower() == title_norm:
        return True
    if not any(c.isalnum() for c in core):
        return True

    return False


def to_spoken(unit: str) -> str:
    """Render one markdown unit to clean spoken text: emphasis → inner text, link →
    anchor text (URL dropped), heading/list markers dropped, a code block → a short
    placeholder (the interim spoken form for code), a table → header-aware prose."""
    if _FENCE.match(unit):
        return "Code sample."

    if _TABLE_ROW.match(unit.lstrip().split("\n", 1)[0]):
        return _table_to_spoken(unit)

    out: list[str] = []

    for tok in _md.parse(unit):
        if tok.type != "inline":
            continue

        for child in tok.children or []:
            if child.type in ("text", "code_inline"):
                out.append(child.content)
            elif child.type in ("softbreak", "hardbreak"):
                out.append(" ")

    # Run-in emphasis that fails CommonMark's flanking rule (`review.**Agents`) is left as
    # literal markers by the parser, so the sanitize tail still has markers to clear.
    return sanitize_spoken("".join(out))


def is_unspeakable(spoken: str) -> bool:
    """True when a spoken form carries no letter or digit (a section-break ornament, bare
    punctuation, or nothing at all): the synthesizer produces no audio for it, so the unit
    it belongs to is dropped."""
    return not any(c.isalnum() for c in spoken)


def sanitize_spoken(text: str) -> str:
    """Turn any leftover markdown emphasis or code marker into a space (splitting the fused
    word or sentence), drop the space a marker left before punctuation, and collapse runs of
    whitespace. The same tail guards two producers: parsed markdown, whose invalid run-in
    emphasis leaks a literal marker, and the describer's structured output, which a JSON
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
