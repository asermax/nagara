"""The load-bearing module: one markdown extraction → display[] units → spoken[] units.

Mechanism (c) from the one-pager: a single trafilatura markdown extraction is the source
of truth. display[i] carries markdown; spoken[i] is derived from it by stripping syntax.
Same segmentation, same index — so the TTS's index-keyed timeline zips onto both for free.
"""

import re

import trafilatura
from markdown_it import MarkdownIt

_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")
_FENCE = re.compile(r"^\s*(```|~~~)")
_BLOCKQUOTE = re.compile(r"^\s*>")
_TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")

_md = MarkdownIt("commonmark").enable("table")


def extract_markdown(html: str) -> str:
    md = trafilatura.extract(
        html,
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=False,
        favor_precision=True,
        include_comments=False,
    )
    if not md:
        raise ValueError("no markdown extracted")

    return md


def split_units(md: str) -> list[str]:
    """Split markdown into display units. Boundary = blank line (markdown mode hard-wraps
    paragraphs across single \\n). A paragraph block's soft-wraps are joined; a list block
    is split into per-item units; a fenced code block stays one atomic unit."""
    units: list[str] = []

    for block in re.split(r"\n[ \t]*\n", md):
        block = block.strip("\n")
        if not block.strip():
            continue

        if _FENCE.match(block):  # fenced code — atomic, internal newlines preserved
            units.append(block)
            continue

        lines = block.split("\n")
        if all(_TABLE_ROW.match(ln) for ln in lines if ln.strip()):
            units.append(block)  # keep raw rows so markdown-it parses the table
            continue             # (joining them would leak `|` pipes into spoken)
        if all(_BLOCKQUOTE.match(ln) for ln in lines if ln.strip()):
            units.append(block)  # keep raw `>` lines so markdown-it parses the quote
            continue             # (joining them would leak a mid-text `>` into spoken)
        if any(_LIST_ITEM.match(ln) for ln in lines):
            units.extend(_split_list_items(lines))
        else:  # paragraph or heading — join soft-wraps into one line
            units.append(" ".join(ln.strip() for ln in lines))

    return units


def _split_list_items(lines: list[str]) -> list[str]:
    """A list block: each marker line starts an item; non-marker lines are soft-wrap
    continuations folded into the current item."""
    items: list[str] = []

    for line in lines:
        if _LIST_ITEM.match(line):
            items.append(line.strip())
        elif items:
            items[-1] += " " + line.strip()

    return items


def to_spoken(unit_md: str) -> str:
    """Render one markdown unit to clean spoken text: emphasis → inner text, link →
    anchor text (URL dropped), heading/list markers dropped, code fence → a placeholder
    (reading code aloud is noise, but the unit must stay index-aligned). Restores the word
    boundary trafilatura drops at emphasis adjacencies (`**phrase**word` → "phrase word")."""
    if _FENCE.match(unit_md):
        return "Code sample."

    if _TABLE_ROW.match(unit_md.lstrip().split("\n", 1)[0]):
        return _table_to_spoken(unit_md)

    out: list[str] = []
    boundary = False  # just crossed an emphasis/link edge → maybe a space was dropped

    def emit_text(content: str) -> None:
        nonlocal boundary
        if not content:
            return
        if boundary and out and out[-1][-1:].isalnum() and content[:1].isalnum():
            out.append(" ")
        out.append(content)
        boundary = False

    for tok in _md.parse(unit_md):
        if tok.type != "inline":
            continue
        for child in tok.children or []:
            if child.type in ("text", "code_inline"):
                emit_text(child.content)
            elif child.type in ("softbreak", "hardbreak"):
                out.append(" ")
                boundary = False
            elif child.type.endswith("_close"):
                boundary = True  # only the CLOSE edge drops a space (`**phrase**word`);
                # the open edge keeps its space, and flagging it would over-split
                # intra-word emphasis (`super**b**` → "super b"). URL (in attrs) ignored.
            elif child.type.endswith("_open"):
                boundary = False

    spoken = "".join(out)

    # Residual pass: trafilatura emits CommonMark-INVALID run-in bold — a closing `**`
    # preceded by punctuation and followed by a letter (`review.**Agents`) fails the
    # flanking rule, so markdown-it leaves the literal markers. Turn any leftover emphasis
    # marker into a space (splitting the word/sentence trafilatura fused), then tidy.
    spoken = re.sub(r"\*\*|__|\*|`", " ", spoken)
    spoken = re.sub(r"\s+([,.;:!?])", r"\1", spoken)

    return re.sub(r"\s+", " ", spoken).strip()


def _table_to_spoken(table_md: str) -> str:
    """Linearize a markdown table into header-aware prose ("Col: value, Col: value.")
    so it reads instead of speaking `|` pipes. Reading a raw table aloud is noise; this
    is a reasonable default, but the *right* spoken form for tables is a parked follow-up."""
    rows, cur = [], []
    for tok in _md.parse(table_md):
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


def pipeline(html: str) -> tuple[list[str], list[str], list[str]]:
    """html → (display[], spoken[], dropped[]) — display/spoken are same length, same
    index by construction. A unit whose spoken form is empty (e.g. a bare footnote ref, an
    image-only unit) is dropped from *both* arrays so the index 1:1 holds and no empty
    string is ever sent to Kokoro (which would raise / yield a zero-duration window)."""
    display, spoken, dropped = [], [], []

    for unit in split_units(extract_markdown(html)):
        if not unit.strip():
            continue
        said = to_spoken(unit)
        if not said:
            dropped.append(unit)
            continue
        display.append(unit)
        spoken.append(said)

    return display, spoken, dropped
