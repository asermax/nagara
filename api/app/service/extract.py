import re

from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
_FENCE = re.compile(r"^[ ]{0,3}(```|~~~)")
_HEADING = re.compile(r"^\s*#{1,6}\s+")

# CommonMark's inline-HTML tag shape, drawn on markdown-it's own boundary: `<T>`, `<br/>` and
# `<not a tag>` are tags to the parser, while `3 < 4`, `<3` and the autolink `<a@b.com>` are not.
# A tag still present in a unit's markdown is prose the author escaped rather than leaked markup:
# the words inside it are the article's own.
_TAG_SHAPE = r"</?([A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*?)?)\s*/?>"
# The spoken strip also takes the escaped form: a table cell is read off the raw inline source,
# where the backslash escaping the tag in the display is still sitting in front of it.
_SPOKEN_HTML_TAG = re.compile(rf"\\?{_TAG_SHAPE}")

# A whole run of one marker character, so `**` between spaces is judged as one marker rather than
# as two asterisks that each touch the other.
_MARKER = re.compile(r"\*+|`+|_{2,}")

_OPERATOR_WORDS = {
    "<=": "less than or equal to",
    ">=": "greater than or equal to",
    "->": "to",
    "=>": "to",
    "<-": "from",
    "<<": "much less than",
    ">>": "much greater than",
    "<3": "heart",
    "<": "less than",
    ">": "greater than",
}
# Longest match first, so `<=` is never read as "less than" followed by a stray `=`. `<3` only
# stands alone: `<30` and `<3.5` are a bound, not a heart.
_OPERATOR = re.compile(
    "|".join(
        rf"{re.escape(op)}(?!\.?\d)" if op == "<3" else re.escape(op)
        for op in sorted(_OPERATOR_WORDS, key=len, reverse=True)
    )
)

_TASK_BOX = re.compile(r"^\[[ xX]\]\s+")

_md = MarkdownIt("commonmark").enable(["table", "strikethrough"])


def is_cruft(text: str, title_norm: str) -> bool:
    """True when the text echoes the article title or carries no letter or digit, comparing
    against the text with any leading markdown marker removed, since a `#`/list prefix would
    otherwise defeat the match."""
    core = _LIST_ITEM.sub("", _HEADING.sub("", text)).strip()

    if title_norm and core.lower() == title_norm:
        return True

    return is_unspeakable(core)


def to_spoken(unit: str) -> str:
    """Render one markdown unit to clean spoken text, one line per block: emphasis and
    strikethrough → inner text, link → anchor text (URL dropped), heading/quote markers dropped,
    a list item on its own line (an ordered one keeps its number), a code block → a short
    placeholder (the interim spoken form for code), a table → a header line then one
    header-aware line per row."""
    if _FENCE.match(unit):
        return "Code sample."

    # Run-in emphasis that fails CommonMark's flanking rule (`review.**Agents`) is left as
    # literal markers by the parser, so the sanitize tail still has markers to clear.
    return sanitize_spoken("\n".join(_block_lines(SyntaxTreeNode(_md.parse(unit)))))


def _block_lines(node: SyntaxTreeNode) -> list[str]:
    if node.type == "inline" and node.token is not None:
        return [_inline_text(node.token)]

    if node.type == "table":
        return _table_lines(node)

    if node.type == "ordered_list":
        start = int(node.attrs.get("start", 1))

        return [
            line
            for number, item in enumerate(node.children, start)
            for line in _item_lines(item, f"{number}. ")
        ]

    if node.type == "bullet_list":
        return [line for item in node.children for line in _item_lines(item, "")]

    return [line for child in node.children for line in _block_lines(child)]


def _item_lines(item: SyntaxTreeNode, marker: str) -> list[str]:
    """An item's marker and checkbox go on its own first paragraph. An item that opens with a
    nested list instead is a split list's resumed empty item: it has no line of its own, and its
    nested items keep their own numbering."""
    lines = [line for child in item.children for line in _block_lines(child)]

    if item.children and item.children[0].type == "paragraph":
        lines[0] = marker + _TASK_BOX.sub("", lines[0])

    return lines


def _inline_text(inline: Token) -> str:
    out: list[str] = []

    for child in inline.children or []:
        if child.type in ("text", "code_inline"):
            out.append(child.content)
        elif child.type in ("softbreak", "hardbreak"):
            out.append(" ")

    return "".join(out)


def is_unspeakable(spoken: str) -> bool:
    """True when a spoken form carries no letter or digit (a section-break ornament, bare
    punctuation, or nothing at all): the synthesizer produces no audio for it, so the unit
    it belongs to is dropped."""
    return not any(c.isalnum() for c in spoken)


def sanitize_spoken(text: str) -> str:
    """Turn any leftover markdown emphasis or code marker that touches text into a space
    (splitting the fused word or sentence), drop the space a marker left before punctuation,
    and collapse runs of whitespace within each line, keeping the newlines between lines. The
    same tail guards two producers: parsed markdown, whose invalid run-in emphasis leaks a
    literal marker, and the describer's structured output, which a JSON schema cannot forbid a
    marker from carrying inside its string value. A leaked marker is only ever caught by playing
    the audio, so both paths run through here.

    It also reduces an XML-like tagged word to the words inside it (`<software>` → software),
    escaped or not: escaped is the shape a table cell arrives in, since ``_table_lines``
    reads a cell off the raw inline source. What angle brackets are left after that, and the
    arrows, are operators, read as their words."""
    text = _SPOKEN_HTML_TAG.sub(r"\1", text)
    text = _MARKER.sub(lambda m: " " if _touches_text(m) else m.group(), text)
    text = _OPERATOR.sub(lambda m: f" {_OPERATOR_WORDS[m.group()]} ", text)

    return "\n".join(line for line in map(_collapse_line, text.split("\n")) if line)


def _collapse_line(line: str) -> str:
    return re.sub(r"\s+([,.;:!?])", r"\1", re.sub(r"\s+", " ", line)).strip()


def _touches_text(marker: re.Match[str]) -> bool:
    """An asterisk between spaces is arithmetic (`value_0 * 2`), not emphasis, so a marker is
    only a leftover when a non-space character sits on either side of it."""
    text, start, end = marker.string, marker.start(), marker.end()

    return (start > 0 and not text[start - 1].isspace()) or (end < len(text) and not text[end].isspace())


def _table_lines(table: SyntaxTreeNode) -> list[str]:
    """Linearize a markdown table into a header line and one header-aware line per body row
    ("Col: value, Col: value.") so it reads instead of speaking pipe characters. Cells carry raw
    inline markup (a `code` span reads its literal backtick), which the sanitize tail clears
    along with the rest of the unit."""
    header, *body = (
        [cell.children[0].content if cell.children else "" for cell in row.children]
        for section in table.children
        for row in section.children
    )

    return [
        ", ".join(header) + ".",
        *(", ".join(f"{name}: {cell}" for name, cell in zip(header, row)) + "." for row in body),
    ]
