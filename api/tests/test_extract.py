import pytest

from app.service.extract import is_cruft, is_unspeakable, sanitize_spoken, to_spoken


def test_plain_text_spoken_equals_display():
    assert to_spoken("Para one.") == "Para one."


def test_soft_wraps_read_as_one_line():
    assert to_spoken("A wrapped\nparagraph here.") == "A wrapped paragraph here."


def test_an_ordered_item_keeps_its_number_from_the_list_start():
    assert to_spoken("3. Write the interface\n4. Implement it") == "3. Write the interface\n4. Implement it"


@pytest.mark.parametrize("unit, expected", [("# The Title", "The Title"), ("## A Section", "A Section")])
def test_a_heading_reads_as_its_words(unit, expected):
    assert to_spoken(unit) == expected


def test_a_quote_reads_each_paragraph_on_its_own_line_without_its_marker():
    assert to_spoken("> First quoted.\n>\n> Second quoted.") == "First quoted.\nSecond quoted."


def test_two_paragraphs_in_one_unit_never_fuse():
    assert to_spoken("First paragraph\n\nSecond paragraph") == "First paragraph\nSecond paragraph"


def test_each_unordered_item_is_its_own_line_with_no_full_stop_added():
    assert to_spoken("- First item\n- Second item\n- Third item") == "First item\nSecond item\nThird item"


def test_nested_lists_read_in_document_order_with_their_own_numbering():
    md = "1. Outer one\n   - Middle\n     1. Inner one\n     2. Inner two\n2. Outer two"
    assert to_spoken(md) == "1. Outer one\nMiddle\n1. Inner one\n2. Inner two\n2. Outer two"


def test_an_item_opening_with_a_nested_list_has_no_line_of_its_own():
    assert to_spoken("2.  3.  Inner item\n3. Outer item") == "3. Inner item\n3. Outer item"


def test_a_code_block_or_image_inside_a_list_item_is_silent_while_the_item_text_reads():
    md = (
        "- Install it:\n\n  ```sh\n  npm install tool\n  ```\n"
        "- See the chart ![A chart of requests](https://example.test/chart.png)\n"
        "- Done"
    )
    assert to_spoken(md) == "Install it:\nSee the chart\nDone"


def test_a_task_checkbox_is_silent_whether_checked_or_not():
    assert to_spoken("- [x] a\n- [ ] b") == "a\nb"


def test_struck_through_text_reads_as_its_words():
    assert to_spoken("~~rejection~~ redirection") == "rejection redirection"


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


def test_a_table_reads_its_header_line_then_one_line_per_row():
    md = "| Feature | Status |\n| --- | --- |\n| Extraction | done |\n| Timing | exact |"
    assert to_spoken(md) == "Feature, Status.\nFeature: Extraction, Status: done.\nFeature: Timing, Status: exact."


def test_table_cell_inline_code_is_sanitized_from_spoken():
    # A cell carrying an inline `code` span must not read its literal backtick: the linearized
    # table runs through the same sanitize tail as every other spoken path.
    md = "| Name | Type |\n| --- | --- |\n| count | `int` |\n| ratio | `float` |"
    assert to_spoken(md) == "Name, Type.\nName: count, Type: int.\nName: ratio, Type: float."


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
    "unit, expected",
    [
        ("a <= b", "a less than or equal to b"),
        ("a >= b", "a greater than or equal to b"),
        ("x -> y", "x to y"),
        ("x => y", "x to y"),
        ("x <- y", "x from y"),
        ("a << b", "a much less than b"),
        ("a >> b", "a much greater than b"),
        ("I <3 tea", "I heart tea"),
        ("a < b", "a less than b"),
        ("a > b", "a greater than b"),
        ("3 <= 4 < 5", "3 less than or equal to 4 less than 5"),
        ("a<b", "a less than b"),
        ("x <30 ms", "x less than 30 ms"),
    ],
)
def test_an_operator_reads_as_its_words_longest_match_first(unit, expected):
    assert to_spoken(unit) == expected


def test_an_asterisk_between_spaces_stays():
    assert to_spoken("It scales by value_0 * 2^{-d} each step.") == "It scales by value_0 * 2^{-d} each step."


def test_a_marker_touching_text_is_stripped_but_a_spaced_one_stays():
    assert sanitize_spoken("a **b** c ** d") == "a b c ** d"


def test_the_tail_keeps_newlines_and_collapses_whitespace_within_a_line():
    assert sanitize_spoken("  one   line .\n\n two\tline ") == "one line.\ntwo line"


def test_a_tagged_word_in_prose_reads_its_word():
    assert to_spoken("Ship \\<software> before the \\</div> closer.") == "Ship software before the div closer."


def test_autolink_still_reads_as_its_target():
    assert to_spoken("Mail <a@b.com> or read <https://x.test> now.") == "Mail a@b.com or read https://x.test now."


def test_tagged_word_in_a_table_cell_reads_its_words():
    # _table_lines reads a cell off the raw inline source, where the escaping backslash is
    # still in front of the tag, so the spoken strip must take that shape.
    md = "| Name | Tag |\n| --- | --- |\n| widget | \\<software> |"
    assert to_spoken(md) == "Name, Tag.\nName: widget, Tag: software."


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


@pytest.mark.parametrize("spoken", ["", "❦", "* * *", "§", "—"])
def test_a_spoken_form_with_no_letter_or_digit_is_unspeakable(spoken):
    assert is_unspeakable(spoken)


@pytest.mark.parametrize("spoken", ["日本語の段落です。", "42", "Code sample.", "Ünïcödé"])
def test_a_spoken_form_with_a_letter_or_digit_is_speakable(spoken):
    assert not is_unspeakable(spoken)
