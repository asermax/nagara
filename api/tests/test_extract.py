from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import trafilatura

from app.service.extract import (
    ExtractionError,
    _normalize_display,
    extract_article,
    units_from_markdown,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _response(content_type="text/html; charset=utf-8", data=b"<html></html>"):
    r = MagicMock()
    r.data = data
    r.html = "<html></html>"
    r.status = 200
    r.headers = {"Content-Type": content_type}
    return r


def display_of(units):
    return [u.display for u in units]


def spoken_of(units):
    return [u.spoken for u in units]


def types_of(units):
    return [u.type for u in units]


# --- extract_article: fetch, content-type gate, title -------------------------


def test_real_fixture_extracts_a_trustworthy_paragraph_split():
    # The only offline input exercising the full fetch-to-extract path against real
    # trafilatura output rather than a hardcoded markdown string: only fetch_response is
    # mocked (to avoid a network call), so trafilatura's own extract/extract_metadata run
    # for real. This is the clean-blog fixture used throughout experiments 001 and 002
    # (Mitchell Hashimoto's "My AI Adoption Journey").
    html = (FIXTURES / "my-ai-adoption-journey.html").read_text()
    response = MagicMock()
    response.data = html.encode()
    response.html = html
    response.status = 200
    response.headers = {"Content-Type": "text/html; charset=utf-8"}

    with patch("app.service.extract.trafilatura.fetch_response", return_value=response):
        title, units = extract_article("https://mitchellh.com/writing/my-ai-adoption-journey")

    assert title == "My AI Adoption Journey"
    assert len(units) > 20  # a real article-length split, not a degenerate one
    # the echoed title and the "Table of Contents" nav label are both dropped, per _is_cruft
    spoken = spoken_of(units)
    assert not any(p.strip().lower() == title.lower() for p in spoken)
    assert not any(p.strip().lower() == "table of contents" for p in spoken)


@patch("app.service.extract.trafilatura")
def test_html_returns_display_and_spoken(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = "# A Title\n\nRead the **repo** for [details](https://x.io)."
    mock_traf.extract_metadata.return_value = MagicMock(title="A Title")

    title, units = extract_article("https://example.test/post")

    assert title == "A Title"
    # the title heading is dropped as an echoed title; the body paragraph carries markdown
    assert display_of(units) == ["Read the **repo** for [details](https://x.io)."]
    assert spoken_of(units) == ["Read the repo for details."]


@patch("app.service.extract.trafilatura")
def test_non_html_clean_fails(mock_traf):
    mock_traf.fetch_response.return_value = _response(content_type="application/pdf")
    with pytest.raises(ExtractionError, match="unsupported content-type"):
        extract_article("https://example.test/doc.pdf")


@patch("app.service.extract.trafilatura")
def test_fetch_failure_raises(mock_traf):
    mock_traf.fetch_response.return_value = None
    with pytest.raises(ExtractionError, match="fetch: no response"):
        extract_article("https://example.test")


@patch("app.service.extract.trafilatura")
def test_empty_extraction_raises(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = None
    with pytest.raises(ExtractionError, match="no article text"):
        extract_article("https://example.test")


@patch("app.service.extract.trafilatura")
def test_all_cruft_extraction_raises(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = "# My Title\n\n## Table of Contents\n\n---"
    mock_traf.extract_metadata.return_value = MagicMock(title="My Title")
    with pytest.raises(ExtractionError, match="no paragraphs"):
        extract_article("https://example.test")


# --- units_from_markdown: segmentation + strip ---------------------------


def test_plain_text_display_equals_spoken():
    units = units_from_markdown("Para one.\n\nPara two.", None)
    assert display_of(units) == ["Para one.", "Para two."]
    assert spoken_of(units) == display_of(units)


def test_soft_wraps_join_into_one_unit():
    units = units_from_markdown("A wrapped\nparagraph here.", None)
    assert display_of(units) == ["A wrapped paragraph here."]


def test_list_splits_per_item():
    units = units_from_markdown("- alpha\n- beta\n- gamma", None)
    assert display_of(units) == ["- alpha", "- beta", "- gamma"]
    assert spoken_of(units) == ["alpha", "beta", "gamma"]


def test_nested_list_item_is_its_own_unit():
    units = units_from_markdown("- parent\n  - child", None)
    assert display_of(units) == ["- parent", "- child"]
    assert spoken_of(units) == ["parent", "child"]


def test_heading_marker_dropped_from_spoken():
    units = units_from_markdown("## A Section", None)
    assert display_of(units) == ["## A Section"]
    assert spoken_of(units) == ["A Section"]


def test_link_reduces_to_anchor_text():
    units = units_from_markdown("See [the docs](https://example.test/x).", None)
    assert spoken_of(units) == ["See the docs."]
    assert "https" not in spoken_of(units)[0]


def test_valid_emphasis_boundary_space_restored():
    units = units_from_markdown("Deep **sessions**where they run.", None)
    assert spoken_of(units) == ["Deep sessions where they run."]


def test_run_in_bold_invalid_markdown_stripped():
    # trafilatura emits a closing ** preceded by punctuation and followed by a letter,
    # which is CommonMark-invalid — the residual pass must still strip it.
    units = units_from_markdown("**Issue and PR review.**Agents help.", None)
    assert "**" not in spoken_of(units)[0]
    assert spoken_of(units) == ["Issue and PR review. Agents help."]


def test_code_block_is_atomic_with_placeholder_spoken():
    md = "```python\ndef f():\n    return 1\n```"
    units = units_from_markdown(md, None)
    assert display_of(units) == [md]
    assert spoken_of(units) == ["Code sample."]


def test_code_block_with_internal_blank_line_stays_atomic():
    md = "```python\ndef f():\n    return 1\n\n\ndef g():\n    return 2\n```"
    units = units_from_markdown(md, None)
    assert display_of(units) == [md]
    assert spoken_of(units) == ["Code sample."]


def test_table_linearizes_to_header_aware_prose():
    md = "| Feature | Status |\n| --- | --- |\n| Extraction | done |\n| Timing | exact |"
    units = units_from_markdown(md, None)
    assert display_of(units) == [md]
    assert spoken_of(units) == ["Feature: Extraction, Status: done. Feature: Timing, Status: exact."]


def test_blockquote_strips_marker():
    units = units_from_markdown("> a quoted line\n> and more", None)
    assert ">" not in spoken_of(units)[0]
    assert spoken_of(units) == ["a quoted line and more"]


def test_empty_spoken_unit_dropped_from_both():
    md = "Real paragraph.\n\n![alt](https://example.test/i.png)\n\nAnother paragraph."
    units = units_from_markdown(md, None)
    assert display_of(units) == ["Real paragraph.", "Another paragraph."]
    assert len(display_of(units)) == len(spoken_of(units))


def test_marker_aware_cleanup_drops_title_and_nav_and_cruft():
    md = "# My Title\n\n## Table of Contents\n\n-\n\nReal one.↩\n\nReal two."
    units = units_from_markdown(md, "My Title")
    assert display_of(units) == ["Real one.", "Real two."]
    assert spoken_of(units) == ["Real one.", "Real two."]


# --- provisional type tagging: fence -> code, everything else -> paragraph -----


def test_provisional_type_tags_fence_as_code_and_prose_as_paragraph():
    md = "A paragraph.\n\n```\ncode\n```\n\n- an item\n\n> a quote"
    units = units_from_markdown(md, None)
    assert types_of(units) == ["paragraph", "code", "paragraph", "paragraph"]


# --- display normalization: emphasis-boundary repair --------------------------


@pytest.mark.parametrize(
    "unit, expected",
    [
        # AC1 — run-in closing delimiter gains a boundary and parses as valid emphasis
        ("**bold phrase**text after", "**bold phrase** text after"),
        ("**text.**Next word", "**text.** Next word"),
        ("a *italic*next word", "a *italic* next word"),
        # AC2 — stray space before the closer is trimmed, revalidating the emphasis
        ("**Cron jobs: **many devs", "**Cron jobs:** many devs"),
        # AC3 — a closing emphasis that abuts a link is separated, link intact
        ("**Fix tests. **[a](http://u)", "**Fix tests.** [a](http://u)"),
    ],
)
def test_normalize_repairs_run_in_emphasis(unit, expected):
    assert _normalize_display(unit) == expected


@pytest.mark.parametrize(
    "unit",
    [
        # AC4 — already-clean, close-before-punct, close-at-end are all no-ops
        "a normal **bold** word here",
        "**work**. Back in time",
        "ends here **bold**",
        # AC5 — non-emphasis delimiter content is never turned into emphasis
        "foo_bar_baz and snake_case_var here",
        "compute 2 * 3 * 4 today",
        # degenerate — no emphasis at all
        "a plain paragraph with no markup",
    ],
)
def test_normalize_leaves_clean_and_non_emphasis_untouched(unit):
    assert _normalize_display(unit) == unit


def test_normalize_adjacent_runs_only_separate_fused_tail():
    assert _normalize_display("**a****b**c and on") == "**a****b** c and on"


@pytest.mark.parametrize(
    "unit",
    [
        # AC6 — delimiter characters inside protected regions pass through verbatim
        "call `a**b**c` inline here",
        "see [text](http://x/a**b**c) now",
        "an ![alt](http://x/a**b**c) image",
    ],
)
def test_normalize_protects_code_and_urls(unit):
    assert _normalize_display(unit) == unit


def test_normalize_skips_fenced_code_block():
    unit = "```python\nf(**kwargs)\nx **y** z\n```"
    assert _normalize_display(unit) == unit


def test_normalize_separates_closer_from_following_code_span():
    # the code span is masked before emphasis repair, but a closer abutting it must still
    # gain a boundary so the two do not render fused
    assert _normalize_display("**bold**`code` after") == "**bold** `code` after"


@pytest.mark.parametrize(
    "unit, expected",
    [
        # a code-span closer fused to the next word gains a boundary
        ("`code`word", "`code` word"),
        ("`None`and", "`None` and"),
        # a code-span closer fused to a following link destination
        ("`quit()`[Python 3.13](https://x)", "`quit()` [Python 3.13](https://x)"),
        # a link destination fused to the next token
        ("[AGENTS.md](https://x/y)(or", "[AGENTS.md](https://x/y) (or"),
    ],
)
def test_normalize_repairs_run_in_code_span_and_link(unit, expected):
    assert _normalize_display(unit) == expected


@pytest.mark.parametrize(
    "unit",
    [
        # left alone — punctuation after a code span does not fuse
        "`python3`. On many systems, `python` now",
        # left alone — an already-spaced code span is bounded
        "`exit` and `quit` commands",
        # left alone — a fenced block is not a span
        "```\nx = 1\n```",
    ],
)
def test_normalize_leaves_spaced_punctuated_and_fenced_code(unit):
    assert _normalize_display(unit) == unit


def test_code_span_and_link_boundaries_keep_spoken_words_separate():
    # trafilatura drops the space after an inline code span and after a link destination; the
    # display repair restores it, and because the normalized display feeds _to_spoken, the
    # spoken words stay separate too. The link case (`(or`) is the one _to_spoken's own
    # close-side boundary flag misses, since the following token does not start with a word.
    code = units_from_markdown("Return `None`and exit.", None)
    assert display_of(code) == ["Return `None` and exit."]
    assert spoken_of(code) == ["Return None and exit."]

    link = units_from_markdown("See [AGENTS.md](https://x/y)(or the guide.", None)
    assert display_of(link) == ["See [AGENTS.md](https://x/y) (or the guide."]
    assert spoken_of(link) == ["See AGENTS.md (or the guide."]


def test_normalize_repairs_inside_blockquote_and_table_preserving_structure():
    assert _normalize_display("> quote **bold**word") == "> quote **bold** word"

    table = "| **Col**name | value |"
    normalized = _normalize_display(table)
    assert normalized == "| **Col** name | value |"
    assert normalized.count("|") == table.count("|")


def test_normalize_is_idempotent():
    for unit in ("**bold phrase**text", "**Cron jobs: **many", "**Fix tests. **[a](http://u)"):
        once = _normalize_display(unit)
        assert _normalize_display(once) == once


def test_display_list_carries_normalized_markdown_spoken_unchanged():
    # a run-in closing ** would render fused; display is repaired while spoken stays clean
    units = units_from_markdown("**Where it began.**A year ago it started.", None)
    assert display_of(units) == ["**Where it began.** A year ago it started."]
    assert spoken_of(units) == ["Where it began. A year ago it started."]
    assert len(display_of(units)) == len(spoken_of(units))


# --- inline-<code>-as-fence repair --------------------------------------------


def test_inline_fence_collapses_to_span_and_next_block_stays_atomic():
    # AC1 — the extractor glues an inline <code> as a mid-line fence (closing fence lone on its own
    # line, as trafilatura emits it); it must collapse to an inline span with the word boundary
    # preserved and NOT corrupt the genuine block that follows it.
    md = (
        "Coordination is expressed through a ```\n        Replica\n```\n base class it knows.\n\n"
        "```\n@Override\nMap<Type, Handler> handlers();\n```"
    )
    units = units_from_markdown(md, None)

    assert display_of(units) == [
        "Coordination is expressed through a `Replica` base class it knows.",
        "```\n@Override\nMap<Type, Handler> handlers();\n```",
    ]
    assert spoken_of(units) == [
        "Coordination is expressed through a Replica base class it knows.",
        "Code sample.",
    ]
    assert types_of(units) == ["paragraph", "code"]


def test_genuine_code_block_untouched_by_inline_fence_repair():
    # AC2 — a real fence opening at line start is not an inline artifact and stays atomic.
    md = "```python\ndef f():\n    return 1\n```"
    units = units_from_markdown(md, None)
    assert display_of(units) == [md]
    assert spoken_of(units) == ["Code sample."]


def test_inline_fence_cascade_keeps_every_genuine_block_atomic():
    # AC3 — the article's shape: artifact -> genuine block -> artifact -> genuine block. Every real
    # block segments as its own atomic unit and each artifact renders with its inline code intact.
    md = (
        "The framework supplies ```\n Replica\n```\n as vocabulary.\n\n"
        "```\nfirst();\n```\n\n"
        "You can write ```\n partition(BYZANTIUM).from(CYRENE)\n```\n in a test.\n\n"
        "```\nsecond();\n```"
    )
    units = units_from_markdown(md, None)

    assert display_of(units) == [
        "The framework supplies `Replica` as vocabulary.",
        "```\nfirst();\n```",
        "You can write `partition(BYZANTIUM).from(CYRENE)` in a test.",
        "```\nsecond();\n```",
    ]
    assert types_of(units) == ["paragraph", "code", "paragraph", "code"]


def test_two_inline_fences_in_one_paragraph_both_collapse():
    # AC4 — two artifacts in the same paragraph, each whitespace-collapsed to a single line.
    md = "Both ```\n foo\n bar\n```\n and ```\n baz\n```\n are terms here."
    units = units_from_markdown(md, None)
    assert display_of(units) == ["Both `foo bar` and `baz` are terms here."]


def test_inline_tilde_fence_is_repaired():
    md = "The ~~~\n Replica\n~~~\n base class it knows."
    units = units_from_markdown(md, None)
    assert display_of(units) == ["The `Replica` base class it knows."]


def test_inline_fence_repair_is_idempotent():
    md = "Coordination through a ```\n Replica\n```\n base class.\n\n```\ncode();\n```"
    once = units_from_markdown(md, None)
    once_display = display_of(once)
    twice = units_from_markdown("\n\n".join(once_display), None)
    assert display_of(twice) == once_display


def test_unbalanced_glued_opener_left_untouched():
    # A glued opener with no lone closing fence is outside the balanced artifact shape: it is not
    # repaired, but it also leaves no line-start fence, so it triggers no segmentation cascade.
    md = "A stray ```opener with no close.\n\n```\ncode();\n```"
    units = units_from_markdown(md, None)
    assert display_of(units) == ["A stray ```opener with no close.", "```\ncode();\n```"]
    assert spoken_of(units)[1] == "Code sample."


def test_unclosed_glued_opener_does_not_swallow_following_block():
    # The content match stops at a paragraph break, so an unbalanced glued opener cannot reach past
    # a blank line to pair with a genuine block's opening fence and cascade it apart.
    md = "A phrase ```\n dangling\n\n```\ncode();\n```"
    units = units_from_markdown(md, None)
    assert display_of(units)[-1] == "```\ncode();\n```"
    assert spoken_of(units)[-1] == "Code sample."


# --- fence segmentation repair: _FENCE tightening, unclosed-opener refusal, fenced-prose guard ---


def test_realpython_fixture_hears_swallowed_prose_and_keeps_genuine_code():
    # The load-bearing fixture (see docs/quest-log/fence-segmentation-repair.md). On this ~360 KB
    # Real Python tutorial, trafilatura emits an unbalanced fence count (one genuinely unclosed
    # fence, plus closed fenced-prose blocks), and the old splitter swallowed thousands of words
    # of article prose as "Code sample." — invisible in a diff, audible only in the audio. Only
    # the real document reproduces it; the fixture cannot be synthesized down.
    html = (FIXTURES / "t17_realpython.html").read_text()
    markdown = trafilatura.extract(
        html,
        url="https://realpython.com/python-first-steps/",
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=True,
        favor_precision=True,
        include_comments=False,
    )
    assert markdown is not None  # the fixture always extracts; narrows trafilatura's str | None
    units = units_from_markdown(markdown, "Python's First Steps")
    code = [u for u in units if u.type == "code"]

    # No prose is trapped behind the code placeholder: a code unit's display is a real snippet,
    # not the thousands of words the old splitter swallowed (the largest was ~1,400 words).
    assert max((len(u.display.split()) for u in code), default=0) < 300
    # The tutorial's real code survived as code, REPL transcripts and plain snippets alike.
    assert len(code) > 30
    # The article's prose is heard: the comparison-expressions paragraph, once trapped in a
    # fenced-prose block spoken as "Code sample.", now reaches the spoken text.
    spoken = " ".join(u.spoken for u in units)
    assert "Boolean" in spoken
    # A real REPL transcript stayed code (proved with a case, not an assertion in prose): the
    # tutorial's first program is a >>> block and remains typed code.
    assert any(u.type == "code" and "Hello, World!" in u.display for u in units)


def test_indented_fence_like_line_does_not_desync_the_toggle():
    # Before _FENCE tightened to CommonMark's three-space limit, the loose ^\s* anchor matched an
    # indented traceback caret (    ~~~^~~) and toggled the fence state, so every following line was
    # swallowed until the next real fence and spoken as "Code sample."
    md = "```\ncode here\n```\n\n    ~~~^~~\n\nThis prose must be a paragraph, never Code sample."
    units = units_from_markdown(md, None)

    assert units[-1].type == "paragraph"
    assert spoken_of(units)[-1] == "This prose must be a paragraph, never Code sample."


def test_unclosed_fence_opener_is_dropped_and_its_prose_heard():
    # A genuinely unclosed fence runs to EOF; opening it would swallow everything after as one
    # code block spoken as "Code sample." The stray opener is dropped and its prose is heard.
    md = (
        "Real intro paragraph.\n\n"
        "```\n"
        "This prose runs to the end with no closing fence.\n"
        "It has several sentences and ordinary words."
    )
    units = units_from_markdown(md, None)

    assert not any(u.type == "code" for u in units)
    spoken = " ".join(spoken_of(units))
    assert "runs to the end" in spoken
    assert "ordinary words" in spoken


def test_fenced_prose_block_reclassifies_to_paragraph_with_fences_stripped():
    md = (
        "```\n"
        "Comparison expressions like these evaluate to the Boolean values True or False.\n"
        "Feel free to play with them in your interactive session.\n"
        "```"
    )
    units = units_from_markdown(md, None)

    assert len(units) == 1
    assert types_of(units) == ["paragraph"]
    assert "```" not in display_of(units)[0]
    assert spoken_of(units) == [
        "Comparison expressions like these evaluate to the Boolean values True or False. "
        "Feel free to play with them in your interactive session."
    ]


def test_fenced_prose_guard_leaves_plain_code_block_as_code():
    # No REPL marker and no comment: the guard must still recognize a real code block by its shape
    # (short, symbol-heavy lines) and leave it typed code.
    md = "```\ndef greet(name):\n    return name\n```"
    units = units_from_markdown(md, None)

    assert types_of(units) == ["code"]
    assert display_of(units) == [md]
    assert spoken_of(units) == ["Code sample."]


def test_fenced_prose_guard_leaves_repl_transcript_as_code():
    # The load-bearing requirement on the guard: a real REPL transcript stays code.
    md = "```\n>>> 2 + 2\n4\n>>> print('hi')\nhi\n```"
    units = units_from_markdown(md, None)

    assert types_of(units) == ["code"]
    assert spoken_of(units) == ["Code sample."]


# --- the hostile fixture: the synthetic probe from experiment 002, pinned as a regression test ---


def test_hostile_fixture_probes_every_construct_class_at_once():
    # This fixture is the synthetic probe from the 002 markdown-paragraph-pipeline experiment
    # (see docs/lab/experiments/markdown-paragraph-pipeline.md): the real article it was run
    # against carried no blockquote and no table, and this is the fixture that caught the
    # blockquote `>` leak the real article never could. Pinned here as an executing assertion
    # instead of a one-off spike script.
    markdown = (FIXTURES / "hostile.md").read_text()
    units = units_from_markdown(markdown, None)
    display = display_of(units)
    spoken = spoken_of(units)

    # paragraph, blockquote, code, 2 list items, table
    assert len(display) == len(spoken) == 6

    # run-in bold glued to the next sentence: display gains the boundary space and stays
    # valid markdown; spoken drops the markers with the boundary restored, not fused.
    assert display[0] == (
        "A paragraph with a [documentation link](https://example.com/docs) and "
        "**a run-in bold heading.** Immediately followed by body text with no space."
    )
    assert spoken[0] == (
        "A paragraph with a documentation link and a run-in bold heading. "
        "Immediately followed by body text with no space."
    )

    # blockquote: the leading `>` on each line must not leak into spoken text.
    assert spoken[1] == "This is a blockquote with some emphasis inside it. It spans two source lines."
    assert ">" not in spoken[1]

    # fenced code block: stays one atomic unit, typed code, spoken as the fixed placeholder.
    assert display[2].startswith("```python")
    assert types_of(units)[2] == "code"
    assert spoken[2] == "Code sample."

    # list: two items, each its own unit, link reduced to anchor text, marker dropped.
    assert display[3] == "- First list item with a [link](https://example.com)."
    assert spoken[3] == "First list item with a link."
    assert display[4] == "- Second item with **bold** and more text."
    assert spoken[4] == "Second item with bold and more text."

    # table: linearizes to header-aware prose rather than leaking pipe characters.
    assert spoken[5] == "Feature: Extraction, Status: done. Feature: Timing, Status: exact."
    assert "|" not in spoken[5]
