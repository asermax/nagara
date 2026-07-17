from unittest.mock import MagicMock, patch

import pytest

from app.service.extract import ExtractionError, extract_article, paragraphs_from_markdown


def _response(content_type="text/html; charset=utf-8", data=b"<html></html>"):
    r = MagicMock()
    r.data = data
    r.html = "<html></html>"
    r.status = 200
    r.headers = {"Content-Type": content_type}
    return r


# --- extract_article: fetch, content-type gate, title -------------------------


@patch("app.service.extract.trafilatura")
def test_html_returns_display_and_spoken(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = "# A Title\n\nRead the **repo** for [details](https://x.io)."
    mock_traf.extract_metadata.return_value = MagicMock(title="A Title")

    title, display, spoken = extract_article("https://example.test/post")

    assert title == "A Title"
    # the title heading is dropped as an echoed title; the body paragraph carries markdown
    assert display == ["Read the **repo** for [details](https://x.io)."]
    assert spoken == ["Read the repo for details."]


@patch("app.service.extract.trafilatura")
def test_non_html_clean_fails(mock_traf):
    mock_traf.fetch_response.return_value = _response(content_type="application/pdf")
    with pytest.raises(ExtractionError, match="unsupported content-type"):
        extract_article("https://example.test/doc.pdf")


@patch("app.service.extract.trafilatura")
def test_fetch_failure_raises(mock_traf):
    mock_traf.fetch_response.return_value = None
    with pytest.raises(ExtractionError, match="fetch failed"):
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


# --- paragraphs_from_markdown: segmentation + strip ---------------------------


def test_plain_text_display_equals_spoken():
    display, spoken = paragraphs_from_markdown("Para one.\n\nPara two.", None)
    assert display == ["Para one.", "Para two."]
    assert spoken == display


def test_soft_wraps_join_into_one_unit():
    display, spoken = paragraphs_from_markdown("A wrapped\nparagraph here.", None)
    assert display == ["A wrapped paragraph here."]


def test_list_splits_per_item():
    display, spoken = paragraphs_from_markdown("- alpha\n- beta\n- gamma", None)
    assert display == ["- alpha", "- beta", "- gamma"]
    assert spoken == ["alpha", "beta", "gamma"]


def test_nested_list_item_is_its_own_unit():
    display, spoken = paragraphs_from_markdown("- parent\n  - child", None)
    assert display == ["- parent", "- child"]
    assert spoken == ["parent", "child"]


def test_heading_marker_dropped_from_spoken():
    display, spoken = paragraphs_from_markdown("## A Section", None)
    assert display == ["## A Section"]
    assert spoken == ["A Section"]


def test_link_reduces_to_anchor_text():
    display, spoken = paragraphs_from_markdown("See [the docs](https://example.test/x).", None)
    assert spoken == ["See the docs."]
    assert "https" not in spoken[0]


def test_valid_emphasis_boundary_space_restored():
    display, spoken = paragraphs_from_markdown("Deep **sessions**where they run.", None)
    assert spoken == ["Deep sessions where they run."]


def test_run_in_bold_invalid_markdown_stripped():
    # trafilatura emits a closing ** preceded by punctuation and followed by a letter,
    # which is CommonMark-invalid — the residual pass must still strip it.
    display, spoken = paragraphs_from_markdown("**Issue and PR review.**Agents help.", None)
    assert "**" not in spoken[0]
    assert spoken == ["Issue and PR review. Agents help."]


def test_code_block_is_atomic_with_placeholder_spoken():
    md = "```python\ndef f():\n    return 1\n```"
    display, spoken = paragraphs_from_markdown(md, None)
    assert display == [md]
    assert spoken == ["Code sample."]


def test_code_block_with_internal_blank_line_stays_atomic():
    md = "```python\ndef f():\n    return 1\n\n\ndef g():\n    return 2\n```"
    display, spoken = paragraphs_from_markdown(md, None)
    assert display == [md]
    assert spoken == ["Code sample."]


def test_table_linearizes_to_header_aware_prose():
    md = "| Feature | Status |\n| --- | --- |\n| Extraction | done |\n| Timing | exact |"
    display, spoken = paragraphs_from_markdown(md, None)
    assert display == [md]
    assert spoken == ["Feature: Extraction, Status: done. Feature: Timing, Status: exact."]


def test_blockquote_strips_marker():
    display, spoken = paragraphs_from_markdown("> a quoted line\n> and more", None)
    assert ">" not in spoken[0]
    assert spoken == ["a quoted line and more"]


def test_empty_spoken_unit_dropped_from_both():
    md = "Real paragraph.\n\n![alt](https://example.test/i.png)\n\nAnother paragraph."
    display, spoken = paragraphs_from_markdown(md, None)
    assert display == ["Real paragraph.", "Another paragraph."]
    assert len(display) == len(spoken)


def test_marker_aware_cleanup_drops_title_and_nav_and_cruft():
    md = "# My Title\n\n## Table of Contents\n\n-\n\nReal one.↩\n\nReal two."
    display, spoken = paragraphs_from_markdown(md, "My Title")
    assert display == ["Real one.", "Real two."]
    assert spoken == ["Real one.", "Real two."]
