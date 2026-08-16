"""Tests for article image selection via DOM containment.

Seam 2: the pure functions in ``app/service/images.py``, driven by HTML fixtures with no
network. The synthetic fixture exercises every path the containment algorithm takes;
the corpus fixture (``t17_realpython.html``) re-runs the measurement table from the quest.
"""
from pathlib import Path

import trafilatura

from app.schemas.items import ParagraphUnit
from app.service.extract import units_from_markdown
from lxml import html as lhtml

from app.service.images import (
    _check_dimensions,
    _find_anchors,
    _find_caption,
    _image_spoken,
    _is_svg,
    _rasterise_svg,
    interleave_image_units,
    select_article_images,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _para(spoken: str) -> ParagraphUnit:
    return ParagraphUnit(type="paragraph", display=spoken, spoken=spoken)


# ---------------------------------------------------------------------------
# Synthetic fixture: exercises containment, og:image, exclusion, ordering
# ---------------------------------------------------------------------------

_SYNTHETIC_HTML = """\
<html>
<head>
  <meta property="og:image" content="https://cdn.example.com/lede.jpg" />
</head>
<body>
  <nav><img src="logo.png" alt="Site Logo" /></nav>

  <article>
    <p>The quick brown fox jumped over the lazy dog in the meadow on a sunny day.</p>

    <figure>
      <img src="fox.jpg" alt="A brown fox leaping" />
    </figure>

    <p>Several researchers have studied fox jumping behaviour across multiple continents.</p>

    <figure>
      <img src="dog.jpg" alt="A sleeping dog" />
    </figure>

    <p>The conclusion was that foxes are extremely agile and lazy dogs do not mind.</p>

    <script type="application/ld+json">
      {"@type": "Article", "articleBody": "The quick brown fox jumped over the lazy dog"}
    </script>
  </article>

  <aside>
    <img src="ad.jpg" alt="Advertisement" />
    <img src="related.jpg" alt="Related article" />
  </aside>
</body>
</html>
"""

_SYNTHETIC_UNITS = [
    _para("The quick brown fox jumped over the lazy dog in the meadow on a sunny day."),
    _para("Several researchers have studied fox jumping behaviour across multiple continents."),
    _para("The conclusion was that foxes are extremely agile and lazy dogs do not mind."),
]


def test_containment_finds_article_images_and_excludes_nav_and_aside():
    candidates = select_article_images(
        _SYNTHETIC_HTML, _SYNTHETIC_UNITS, "https://example.com/article"
    )

    srcs = [c.src for c in candidates]

    assert "https://cdn.example.com/lede.jpg" in srcs
    assert "https://example.com/fox.jpg" in srcs
    assert "https://example.com/dog.jpg" in srcs
    assert "https://example.com/logo.png" not in srcs
    assert "https://example.com/ad.jpg" not in srcs
    assert "https://example.com/related.jpg" not in srcs


def test_og_image_comes_first():
    candidates = select_article_images(
        _SYNTHETIC_HTML, _SYNTHETIC_UNITS, "https://example.com/article"
    )
    assert candidates[0].src == "https://cdn.example.com/lede.jpg"
    assert candidates[0].insert_after == -1


def test_og_image_deduplication():
    html = _SYNTHETIC_HTML.replace(
        'content="https://cdn.example.com/lede.jpg"',
        'content="fox.jpg"',
    )
    candidates = select_article_images(
        html, _SYNTHETIC_UNITS, "https://example.com/article"
    )

    fox_srcs = [c for c in candidates if c.src == "https://example.com/fox.jpg"]
    assert len(fox_srcs) == 1


def test_image_positions_follow_document_order():
    candidates = select_article_images(
        _SYNTHETIC_HTML, _SYNTHETIC_UNITS, "https://example.com/article"
    )

    fox = next(c for c in candidates if "fox" in c.src)
    dog = next(c for c in candidates if "dog" in c.src)

    assert fox.insert_after == 0
    assert dog.insert_after == 1


def test_alt_text_carried_on_candidate():
    candidates = select_article_images(
        _SYNTHETIC_HTML, _SYNTHETIC_UNITS, "https://example.com/article"
    )

    fox = next(c for c in candidates if "fox" in c.src)
    assert fox.alt == "A brown fox leaping"

    lede = next(c for c in candidates if "lede" in c.src)
    assert lede.alt == ""


def test_script_tag_excluded_from_anchoring():
    """The JSON-LD body carries article text but must not become an anchor."""
    from lxml import html as lhtml

    tree = lhtml.fromstring(_SYNTHETIC_HTML)
    anchors = _find_anchors(tree, _SYNTHETIC_UNITS)

    for el, _ in anchors:
        assert el.tag != "script"


def test_no_container_falls_back_to_og_image():
    html = """\
    <html>
    <head><meta property="og:image" content="https://example.com/lede.jpg" /></head>
    <body><p>Short.</p></body>
    </html>
    """
    units = [_para("Short")]
    candidates = select_article_images(html, units, "https://example.com/page")

    assert len(candidates) == 1
    assert candidates[0].src == "https://example.com/lede.jpg"


def test_data_uri_preserved_as_src():
    html = """\
    <html><body><article>
      <p>The quick brown fox jumped over the lazy dog in the meadow on a sunny day.</p>
      <p>Several researchers have studied fox jumping behaviour across multiple continents.</p>
      <img src="data:image/png;base64,iVBORw0KGgo=" alt="Inline" />
      <p>The conclusion was that foxes are extremely agile and lazy dogs do not mind.</p>
    </article></body></html>
    """
    units = [
        _para("The quick brown fox jumped over the lazy dog in the meadow on a sunny day."),
        _para("Several researchers have studied fox jumping behaviour across multiple continents."),
        _para("The conclusion was that foxes are extremely agile and lazy dogs do not mind."),
    ]
    candidates = select_article_images(html, units, "https://example.com/page")

    data_candidates = [c for c in candidates if c.src.startswith("data:")]
    assert len(data_candidates) == 1


# ---------------------------------------------------------------------------
# Interleaving
# ---------------------------------------------------------------------------


def test_interleave_inserts_at_positions():
    from app.schemas.items import ImageUnit

    text = [_para("A"), _para("B"), _para("C")]
    images = [
        (-1, ImageUnit(type="image", display="lede", spoken="Image: lede", image="h0")),
        (0, ImageUnit(type="image", display="fig1", spoken="Image: fig1", image="h1")),
        (2, ImageUnit(type="image", display="fig2", spoken="Image: fig2", image="h2")),
    ]

    result = interleave_image_units(text, images)

    types_and_displays = [(u.type, u.display) for u in result]
    assert types_and_displays == [
        ("image", "lede"),
        ("paragraph", "A"),
        ("image", "fig1"),
        ("paragraph", "B"),
        ("paragraph", "C"),
        ("image", "fig2"),
    ]


def test_interleave_with_no_images_returns_copy():
    text = [_para("A"), _para("B")]
    result = interleave_image_units(text, [])
    assert len(result) == 2
    assert result is not text


# ---------------------------------------------------------------------------
# Corpus fixture: realpython (already in the repo for fence tests)
# ---------------------------------------------------------------------------


def test_realpython_containment():
    """The realpython fixture is the one entry with a known false positive (brand logo).

    Expected: 3 selected (lede + figure + brand logo), 1 false positive.
    """
    html = (FIXTURES / "t17_realpython.html").read_text()
    url = "https://realpython.com/python-first-steps/"

    md = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_formatting=True,
        include_links=True,
        include_tables=True,
        favor_precision=True,
        include_comments=False,
    )
    meta = trafilatura.extract_metadata(html)
    assert md is not None
    units = units_from_markdown(md, meta.title if meta else None)

    candidates = select_article_images(html, units, url)

    assert len(candidates) >= 2
    assert any("og:image" in c.src or c.insert_after == -1 for c in candidates)


# ---------------------------------------------------------------------------
# Figure captions — the top of the image spoken-form precedence
# ---------------------------------------------------------------------------


def test_newyorker_figure_caption_extracted_credit_excluded():
    """The New Yorker wraps a figure caption in a ``caption__text`` span and its credit
    line in a sibling ``CaptionCredit`` span. The caption is taken verbatim; the credit
    ("Photograph by ... / Courtesy ©") is left out."""
    tree = lhtml.fromstring((FIXTURES / "t17_newyorker.html").read_text())

    captions = [
        _find_caption(fig.xpath(".//img")[0]) for fig in tree.xpath("//figure")
    ]

    assert all(caption for caption in captions)
    assert any("Dead Fish, Fire Island" in caption for caption in captions)
    assert not any("Photograph by" in caption for caption in captions)
    assert not any("Courtesy" in caption for caption in captions)


def test_acx_figcaption_extracted():
    tree = lhtml.fromstring((FIXTURES / "acx_figcaption.html").read_text())

    chart = next(img for img in tree.xpath("//img") if img.get("alt") == "a scatter plot")
    caption = _find_caption(chart)

    assert caption == "Predicted versus actual, 2013 to 2023. The fit is better than the eye expects."
    assert "Source" not in caption


def test_no_caption_returns_nothing_not_neighbouring_prose():
    tree = lhtml.fromstring((FIXTURES / "acx_figcaption.html").read_text())

    divider = next(
        img for img in tree.xpath("//img") if img.get("alt") == "a decorative divider"
    )

    assert _find_caption(divider) == ""


def test_image_without_a_figure_has_no_caption():
    """A bare image outside any ``<figure>`` never reaches out for a caption."""
    tree = lhtml.fromstring(
        "<article><p>Some prose.</p><img src='x.png' alt='bare' /></article>"
    )

    assert _find_caption(tree.xpath("//img")[0]) == ""


def test_image_spoken_precedence():
    """Caption outranks alt outranks the floor, and a caption short-circuits."""
    assert _image_spoken("A real caption", "alt text") == "Image: A real caption"
    assert _image_spoken("", "alt text") == "Image: alt text"
    assert _image_spoken("", "") == "Image with no description."


# ---------------------------------------------------------------------------
# Size filter
# ---------------------------------------------------------------------------


def test_check_dimensions_passes_large_image():
    from PIL import Image as PILImage
    from io import BytesIO

    buf = BytesIO()
    PILImage.new("RGB", (400, 300)).save(buf, format="PNG")
    _check_dimensions(buf.getvalue())


def test_check_dimensions_rejects_small_image():
    from PIL import Image as PILImage
    from io import BytesIO
    import pytest

    buf = BytesIO()
    PILImage.new("RGB", (100, 100)).save(buf, format="PNG")

    with pytest.raises(Exception, match="too small"):
        _check_dimensions(buf.getvalue())


# ---------------------------------------------------------------------------
# SVG detection and rasterisation
# ---------------------------------------------------------------------------


def test_svg_detection():
    assert _is_svg(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    assert _is_svg(b'<?xml version="1.0"?>\n<SVG></SVG>')
    assert not _is_svg(b'\x89PNG\r\n\x1a\n')


def test_svg_rasterisation_produces_png():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
    result = _rasterise_svg(svg)
    assert result[:4] == b"\x89PNG"
