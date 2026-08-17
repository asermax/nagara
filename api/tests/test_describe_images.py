"""Tests for the image describer: the case-2-vs-3 filter, the prompt, and the fan-out.

Two seams. One cassette test drives `describe` against a committed fixture image and a recorded
Gemini response, asserting on the HTTP and JSON *shape* — one request, a non-empty sanitized
sentence with no leftover marker and no self-opener — never on the exact wording, which varies by
temperature. Everything else is deterministic and asserted with no network: the good-alt filter
that decides case 2 from case 3, the `Image: ` prefix nagara owns, the failure fallbacks (case 4
verbatim alt, case 5 floor), and the shared code+image budget counted in document order.

The image describer cassette was recorded against a real Gemini key present in this worktree; the
auth header is scrubbed by the central `vcr_config`. Tests assert on shape only, so a re-record
against a fresh key stays green.
"""
import asyncio
from pathlib import Path

import pytest
from google import genai

import app.service.describe as describe_mod
from app.config import settings
from app.schemas.items import CodeUnit, ImageUnit, ParagraphUnit
from app.service.describe import (
    ImageDescribeRequest,
    _image_contents,
    enrich_with_descriptions,
)
from app.service.images import _is_good_alt, _needs_describe
from app.service.storage.image import encode_image

FIXTURES = Path(__file__).parent / "fixtures"

_TITLE = "Python First Steps"
_ALT = ""  # the fixture image carries no alt, so it is a pure case-3 describe
_IMAGE_WEBP = encode_image((FIXTURES / "bakeoff_realpython.jpg").read_bytes())[1]
_REQUEST = ImageDescribeRequest(index=0, alt=_ALT, image=_IMAGE_WEBP)


def _client() -> genai.Client:
    # Real key when recording (present in this worktree), a placeholder on replay — the header is
    # scrubbed and this cassette matches without the body, so the placeholder never reaches a wire.
    return genai.Client(api_key=settings.gemini_api_key or "replay-key")


def _image(alt: str = "", spoken: str | None = None) -> ImageUnit:
    if spoken is None:
        spoken = f"Image: {alt}" if alt else "Image with no description."
    return ImageUnit(type="image", display=alt, spoken=spoken, image="h0")


def _code(spoken: str = "Code sample.") -> CodeUnit:
    return CodeUnit(type="code", display="```\nx = 1\n```", spoken=spoken)


# --- the describer HTTP seam (recorded against a real key, asserts shape) -----


@pytest.mark.vcr(match_on=["method", "scheme", "host", "port", "path", "query"])
def test_image_describe_returns_a_clean_sentence(vcr):
    # The image bytes ride as an inline part; the parsed sentence comes back sanitized, with no
    # marker the JSON schema cannot forbid and no self-opener the prompt bans.
    spoken = asyncio.run(
        describe_mod.describe(_client(), _image_contents(_TITLE, _REQUEST))
    )

    assert spoken
    assert "`" not in spoken and "*" not in spoken
    assert not spoken.startswith(("This", "The image", "An image", "A picture"))
    assert len(vcr.requests) == 1


# --- the good-alt filter: case 2 verbatim vs case 3 describe -------------------


def test_a_real_sentence_alt_is_kept_verbatim():
    # The quest's kept example: a grammatical sentence that is not boilerplate stays case 2.
    assert _is_good_alt("Image of tank rolling over a world map", "the title") is True


def test_a_subscribe_prompt_alt_goes_to_the_describer():
    # A grammatical sentence caught only by the denylist: case 3, not spoken verbatim.
    alt = "This article appears in the October 2023 issue. Subscribe to WIRED."
    assert _is_good_alt(alt, "the title") is False
    assert _needs_describe("", alt, "the title") is True


def test_a_title_as_alt_is_rejected_by_is_cruft():
    # Reusing the extractor's title-echo check: an alt that is the article title is not spoken.
    title = "the surprising history of the semicolon"
    assert _is_good_alt("The Surprising History of the Semicolon", title) is False


def test_seo_keyword_soup_and_filenames_and_empty_go_to_the_describer():
    assert _is_good_alt("wired, technology, ai, future, 2023", "t") is False
    assert _is_good_alt("hero-image-final-v2.jpg", "t") is False
    assert _is_good_alt("", "t") is False


def test_a_present_caption_never_reaches_the_describer():
    assert _needs_describe("A real caption", "anything at all here", "t") is False


# --- the fan-out: prefix, failure fallbacks, shared budget --------------------


def _patch_describe(monkeypatch, fn):
    async def stub(client, contents, *, model=describe_mod.MODEL):
        return await fn(contents)

    monkeypatch.setattr(describe_mod, "describe", stub)


def test_the_image_prefix_is_applied_by_nagara(monkeypatch):
    async def model_sentence(contents):
        # The model returns no self-opener; nagara owns the `Image: ` announcement.
        return "A bar chart comparing runtime across three languages"

    _patch_describe(monkeypatch, model_sentence)

    units = [_image(alt="")]
    result, degradations = asyncio.run(
        enrich_with_descriptions(
            units, _TITLE, image_requests=[_REQUEST], api_key="replay-key"
        )
    )

    assert result[0].spoken == "Image: A bar chart comparing runtime across three languages"
    assert degradations == []


def test_a_describer_failure_falls_back_to_the_failed_case_2_alt(monkeypatch):
    # Case 4: the describer is unreachable, so an alt that failed the case-2 filter (a subscribe
    # prompt) is spoken verbatim rather than left silent — the deliberate inversion of case 2.
    async def always_fail(contents):
        raise RuntimeError("describer down")

    _patch_describe(monkeypatch, always_fail)

    bad_alt = "Subscribe to WIRED for more."
    units = [_image(alt=bad_alt)]
    request = ImageDescribeRequest(index=0, alt=bad_alt, image=b"")
    result, degradations = asyncio.run(
        enrich_with_descriptions(
            units, _TITLE, image_requests=[request], api_key="replay-key"
        )
    )

    assert result[0].spoken == f"Image: {bad_alt}"
    assert degradations == [{"type": "image", "reason": "describe failed"}]


def test_an_empty_alt_failure_produces_the_exact_floor(monkeypatch):
    # Case 5: no alt to fall back to, so the honest floor is what the listener hears.
    async def always_fail(contents):
        raise RuntimeError("describer down")

    _patch_describe(monkeypatch, always_fail)

    units = [_image(alt="")]
    request = ImageDescribeRequest(index=0, alt="", image=b"")
    result, degradations = asyncio.run(
        enrich_with_descriptions(
            units, _TITLE, image_requests=[request], api_key="replay-key"
        )
    )

    assert result[0].spoken == "Image with no description."
    assert degradations == [{"type": "image", "reason": "describe failed"}]


def test_an_image_only_failure_never_fails_the_item(monkeypatch):
    # Unlike code, an all-image-failed article does not raise: every image has a spoken fallback.
    async def always_fail(contents):
        raise RuntimeError("describer down")

    _patch_describe(monkeypatch, always_fail)

    units = [_image(alt="a"), _image(alt="b")]
    requests = [
        ImageDescribeRequest(index=0, alt="a", image=b""),
        ImageDescribeRequest(index=1, alt="b", image=b""),
    ]
    result, degradations = asyncio.run(
        enrich_with_descriptions(
            units, _TITLE, image_requests=requests, api_key="replay-key"
        )
    )

    assert len(result) == 2
    assert degradations == [{"type": "image", "reason": "describe failed"}] * 2


def test_the_shared_budget_floors_code_and_images_in_document_order(monkeypatch):
    # One budget across both kinds: with a cap of 2 over an interleaved [code, image, code,
    # image] list, only the first two jobs describe and the rest fall to their non-describer
    # form — the code to its floor, the image to its alt — each with a cap-reached degradation.
    async def model_sentence(contents):
        return "described"

    _patch_describe(monkeypatch, model_sentence)

    units = [
        _code(spoken="Code sample one."),
        _image(alt="alt one"),
        _code(spoken="Code sample two."),
        _image(alt="alt two"),
    ]
    requests = [
        ImageDescribeRequest(index=1, alt="alt one", image=b""),
        ImageDescribeRequest(index=3, alt="alt two", image=b""),
    ]
    result, degradations = asyncio.run(
        enrich_with_descriptions(
            units,
            _TITLE,
            image_requests=requests,
            api_key="replay-key",
            max_describes=2,
        )
    )

    assert result[0].spoken == "Code: described"
    assert result[1].spoken == "Image: described"
    assert result[2].spoken == "Code with no description."
    assert result[3].spoken == "Image: alt two"
    assert degradations == [
        {"type": "code", "reason": "describe cap reached"},
        {"type": "image", "reason": "describe cap reached"},
    ]


def test_on_describe_fires_with_the_kind_per_successful_image(monkeypatch):
    async def model_sentence(contents):
        return "described"

    _patch_describe(monkeypatch, model_sentence)

    kinds: list[str] = []

    units = [_image(alt=""), _code()]
    result, _ = asyncio.run(
        enrich_with_descriptions(
            units,
            _TITLE,
            image_requests=[_REQUEST],
            api_key="replay-key",
            on_describe=kinds.append,
        )
    )

    assert sorted(kinds) == ["code", "image"]


def test_no_jobs_needs_no_key():
    # A prose-and-captioned-image article has no describe jobs, so no client and no key.
    units = [ParagraphUnit(type="paragraph", display="Prose.", spoken="Prose.")]
    result, degradations = asyncio.run(
        enrich_with_descriptions(units, _TITLE, image_requests=[], api_key="")
    )

    assert result == units
    assert degradations == []
