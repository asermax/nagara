from unittest.mock import MagicMock, patch

import pytest

from app.service.extract import ExtractionError, extract_article


def _response(content_type="text/html; charset=utf-8", data=b"<html></html>"):
    r = MagicMock()
    r.data = data
    r.html = "<html></html>"
    r.status = 200
    r.headers = {"Content-Type": content_type}
    return r


@patch("app.service.extract.trafilatura")
def test_html_returns_paragraphs_and_title(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = "Para one.\nPara two.\nPara three."
    mock_traf.extract_metadata.return_value = MagicMock(title="A Title")

    title, paras = extract_article("https://example.test/post")

    assert title == "A Title"
    assert paras == ["Para one.", "Para two.", "Para three."]


@patch("app.service.extract.trafilatura")
def test_cleanup_drops_title_echo_and_cruft(mock_traf):
    mock_traf.fetch_response.return_value = _response()
    mock_traf.extract.return_value = "My Title\nTable of Contents\n-\nReal one.↩\nReal two."
    mock_traf.extract_metadata.return_value = MagicMock(title="My Title")

    title, paras = extract_article("https://example.test/post")

    assert title == "My Title"
    assert paras == ["Real one.", "Real two."]


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
