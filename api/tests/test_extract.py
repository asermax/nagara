import pytest

from app.service.extract import is_cruft, sanitize_spoken, to_spoken


def test_plain_text_spoken_equals_display():
    assert to_spoken("Para one.") == "Para one."


def test_soft_wraps_read_as_one_line():
    assert to_spoken("A wrapped\nparagraph here.") == "A wrapped paragraph here."


def test_list_marker_dropped_from_spoken():
    assert to_spoken("- alpha") == "alpha"
    assert to_spoken("1. first") == "first"


def test_heading_marker_dropped_from_spoken():
    assert to_spoken("## A Section") == "A Section"


def test_link_reduces_to_anchor_text():
    assert to_spoken("See [the docs](https://example.test/x).") == "See the docs."


def test_emphasis_reads_its_inner_text():
    assert to_spoken("Deep **sessions** where *they* run.") == "Deep sessions where they run."


def test_run_in_bold_invalid_markdown_stripped():
    # A closing ** preceded by punctuation and followed by a letter is CommonMark-invalid,
    # so the parser leaves the literal markers and the sanitize tail must still clear them.
    assert to_spoken("**Issue and PR review.**Agents help.") == "Issue and PR review. Agents help."


def test_code_block_speaks_the_placeholder():
    assert to_spoken("```python\ndef f():\n    return 1\n\n\ndef g():\n    return 2\n```") == "Code sample."


def test_table_linearizes_to_header_aware_prose():
    md = "| Feature | Status |\n| --- | --- |\n| Extraction | done |\n| Timing | exact |"
    assert to_spoken(md) == "Feature: Extraction, Status: done. Feature: Timing, Status: exact."


def test_table_cell_inline_code_is_sanitized_from_spoken():
    # A cell carrying an inline `code` span must not read its literal backtick: the linearized
    # table runs through the same sanitize tail as every other spoken path.
    md = "| Name | Type |\n| --- | --- |\n| count | `int` |\n| ratio | `float` |"
    assert to_spoken(md) == "Name: count, Type: int. Name: ratio, Type: float."


def test_blockquote_strips_marker():
    assert to_spoken("> a quoted line\n> and more") == "a quoted line and more"


def test_image_markdown_speaks_nothing():
    assert to_spoken("![alt](https://example.test/i.png)") == ""


def test_escaped_tagged_word_reads_its_words():
    assert to_spoken("We ship \\<software> to users.") == "We ship software to users."


def test_escaped_tag_only_unit_reads_its_word():
    assert to_spoken("\\<software>") == "software"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("The <div> element.", "The div element."),
        ("Its </div> closer.", "Its div closer."),
        ("A generic <T> parameter.", "A generic T parameter."),
        ("A <br/> void tag.", "A br void tag."),
        ("Set <your-api-key> here.", "Set your-api-key here."),
        ("Set \\<your-api-key> here.", "Set your-api-key here."),
    ],
)
def test_tagged_word_keeps_the_words_inside_whatever_the_tag_shape(text, expected):
    assert sanitize_spoken(text) == expected


@pytest.mark.parametrize(
    "unit",
    [
        # markdown-it reads none of these as a tag, and neither may the strip
        "Angle math: 3 < 4 and 5 > 2.",
        "I <3 hearts and a<b compares.",
    ],
)
def test_angle_brackets_that_are_not_tags_are_untouched(unit):
    assert to_spoken(unit) == unit


def test_autolink_still_reads_as_its_target():
    assert to_spoken("Mail <a@b.com> or read <https://x.test> now.") == "Mail a@b.com or read https://x.test now."


def test_tagged_word_in_a_table_cell_reads_its_words():
    # _table_to_spoken reads a cell off the raw inline source, where the escaping backslash is
    # still in front of the tag, so the spoken strip must take that shape.
    md = "| Name | Tag |\n| --- | --- |\n| widget | \\<software> |"
    assert to_spoken(md) == "Name: widget, Tag: software."


def test_code_span_reads_the_words_of_its_tag():
    assert to_spoken("Use `<software>` inside a code span.") == "Use software inside a code span."


def test_is_cruft_matches_the_title_echo_past_a_heading_marker():
    assert is_cruft("# My Title", "my title")
    assert not is_cruft("My Title, revisited", "my title")


@pytest.mark.parametrize("text", ["-", "❦", "* * *", "§"])
def test_is_cruft_matches_text_with_no_letter_or_digit(text):
    assert is_cruft(text, "")


def test_is_cruft_keeps_a_navigation_label():
    assert not is_cruft("Table of contents", "")
