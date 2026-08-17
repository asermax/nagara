"""Tests for the Gemini describer and its code-block fan-out.

Two seams. The cassette tests drive `describe` against a recorded HTTP response and assert on
the HTTP and JSON *shape*, never the exact sentence: the sentence varies by temperature and
cannot be judged from a test either way. What is deterministic is asserted here — the sanitize
tail strips a marker the schema cannot forbid, a recorded 400 fails without retrying, and a
recorded 429 retries.

The orchestration tests patch `describe` and assert the fan-out's own contract with no network:
the `Code: ` prefix is nagara's, the cap floors past the max in document order, a single failure
degrades, and every unit failing fails the item.

Replay-only at record mode ``none`` (CI adds ``--block-network``). The describer cassettes are
HAND-AUTHORED — no Gemini key was available to record them. Re-record with a real key via
``uv run pytest --record-mode=rewrite tests/test_describe.py`` before trusting them.
"""
import asyncio

import pytest
from google import genai
from google.genai.errors import ClientError

import app.service.describe as describe_mod
from app.config import settings
from app.schemas.items import CodeUnit, ParagraphUnit
from app.service.describe import (
    build_code_prompt,
    describe,
    enrich_with_descriptions,
    sanitize_spoken,
)

# The fixed input the hand-authored cassettes were recorded against. The request body carries
# the whole prompt and vcr matches on body, so a cassette replays only for this exact input.
_TITLE = "Testing Async Python"
_INTRO = "The helper below wraps the retry loop around a single request."
_CODE = "async def fetch(url):\n    return await client.get(url)"
_PROMPT = build_code_prompt(_TITLE, _INTRO, _CODE)


def _client() -> genai.Client:
    # Real key when recording (present in api/.env), a placeholder on replay: the key is never
    # compared on replay (matching is on method/host/path/query/body and the header is scrubbed),
    # and the placeholder keeps replay from falling back to the ambient GOOGLE_API_KEY.
    return genai.Client(api_key=settings.gemini_api_key or "replay-key")


def _code(display: str = "```\nx = 1\n```", spoken: str = "Code sample.") -> CodeUnit:
    return CodeUnit(type="code", display=display, spoken=spoken)


# --- the sanitize prefactor ---------------------------------------------------


def test_sanitize_spoken_turns_leftover_markers_into_spaces():
    # The same tail article prose runs through: a leaked marker splits the fused token rather
    # than being read aloud.
    assert sanitize_spoken("A `code` span and **bold** text.") == "A code span and bold text."
    assert sanitize_spoken("word**next") == "word next"


# --- the describer HTTP seam (hand-authored cassettes) ------------------------


@pytest.mark.vcr
def test_sanitize_tail_strips_a_marker_from_the_response(vcr):
    # The recorded response carries a marker inside the JSON string value — a class structured
    # output cannot forbid — and the parsed sentence comes back with no marker left.
    spoken = asyncio.run(describe(_client(), _PROMPT))

    assert "`" not in spoken
    assert "*" not in spoken
    assert spoken and not spoken.startswith("This")
    assert len(vcr.requests) == 1


@pytest.mark.vcr
def test_a_real_code_describe_parses_and_is_clean(vcr):
    # Recorded against a real Gemini key: proof the text-only code path parses a genuine
    # response envelope, alongside the image cassette that proves the same core with an image
    # part. Asserts shape only — a real sentence, no leaked marker, no self-opener — never the
    # exact words, which vary by temperature.
    spoken = asyncio.run(describe(_client(), _PROMPT))

    assert spoken and not spoken.startswith("This")
    assert "`" not in spoken and "*" not in spoken
    assert len(vcr.requests) == 1


@pytest.mark.vcr
def test_a_400_fails_the_unit_without_retrying(vcr):
    # 400 means the call is wrong, not unlucky, so it raises straight through with no second
    # attempt: exactly one request reaches the cassette.
    with pytest.raises(ClientError) as exc:
        asyncio.run(describe(_client(), _PROMPT))

    assert exc.value.code == 400
    assert len(vcr.requests) == 1


@pytest.mark.vcr
def test_a_429_retries_then_succeeds(vcr):
    # 429 is transient, so stamina retries in place: the first request is throttled, the second
    # succeeds, and the sentence comes back. Two requests reach the cassette.
    spoken = asyncio.run(describe(_client(), _PROMPT))

    assert spoken
    assert len(vcr.requests) == 2


# --- the code-block fan-out (patched describe, no network) --------------------


def _patch_describe(monkeypatch, fn):
    async def stub(client, prompt, *, model=describe_mod.MODEL):
        return await fn(prompt)

    monkeypatch.setattr(describe_mod, "describe", stub)


def test_the_code_prefix_is_applied_by_nagara(monkeypatch):
    async def model_sentence(prompt):
        # The model returns no self-opener; nagara owns the `Code: ` announcement.
        return "A Python function that wraps a single request"

    _patch_describe(monkeypatch, model_sentence)

    units = [ParagraphUnit(type="paragraph", display="Intro.", spoken="Intro."), _code()]
    result, degradations = asyncio.run(
        enrich_with_descriptions(units, _TITLE, api_key="replay-key")
    )

    assert result[1].spoken == "Code: A Python function that wraps a single request"
    assert degradations == []


def test_the_cap_floors_units_past_the_max_in_document_order(monkeypatch):
    async def model_sentence(prompt):
        return "a described sentence"

    _patch_describe(monkeypatch, model_sentence)

    units = [_code(spoken=f"Code sample {i}.") for i in range(30)]
    result, degradations = asyncio.run(
        enrich_with_descriptions(units, _TITLE, api_key="replay-key", max_describes=25)
    )

    assert all(result[i].spoken == "Code: a described sentence" for i in range(25))
    assert all(result[i].spoken == "Code with no description." for i in range(25, 30))
    assert degradations == [{"type": "code", "reason": "describe cap reached"}] * 5


def test_a_single_failure_floors_and_degrades_without_failing(monkeypatch):
    async def flaky(prompt):
        if "RAISE_HERE" in prompt:
            raise RuntimeError("transient-looking but exhausted")
        return "a described sentence"

    _patch_describe(monkeypatch, flaky)

    units = [
        _code(display="```\nRAISE_HERE\n```", spoken="Code sample one."),
        _code(display="```\nfine_here\n```", spoken="Code sample two."),
    ]
    result, degradations = asyncio.run(
        enrich_with_descriptions(units, _TITLE, api_key="replay-key")
    )

    assert result[0].spoken == "Code with no description."
    assert result[1].spoken == "Code: a described sentence"
    assert degradations == [{"type": "code", "reason": "describe failed"}]


def test_on_describe_fires_once_per_successful_describe(monkeypatch):
    # The cost meter counts billed calls: a failed unit made no billable call, so the callback
    # fires only for the two that resolved, never for the one that raised.
    async def flaky(prompt):
        if "RAISE_HERE" in prompt:
            raise RuntimeError("exhausted")
        return "a described sentence"

    _patch_describe(monkeypatch, flaky)

    calls = 0

    def _count(kind: str) -> None:
        nonlocal calls
        calls += 1

    units = [
        _code(display="```\nRAISE_HERE\n```"),
        _code(display="```\nfine_one\n```"),
        _code(display="```\nfine_two\n```"),
    ]
    asyncio.run(
        enrich_with_descriptions(units, _TITLE, api_key="replay-key", on_describe=_count)
    )

    assert calls == 2


def test_every_code_unit_failing_fails_the_item(monkeypatch):
    async def always_fail(prompt):
        raise RuntimeError("down")

    _patch_describe(monkeypatch, always_fail)

    units = [_code(), _code()]
    with pytest.raises(RuntimeError):
        asyncio.run(enrich_with_descriptions(units, _TITLE, api_key="replay-key"))


def test_no_code_units_makes_no_calls_and_needs_no_key():
    # No code means nothing enrichable, so an empty key is fine and no client is built.
    units = [ParagraphUnit(type="paragraph", display="Just prose.", spoken="Just prose.")]
    result, degradations = asyncio.run(enrich_with_descriptions(units, _TITLE, api_key=""))

    assert result == units
    assert degradations == []


def test_a_missing_key_with_code_fails_loudly():
    # A code-bearing item with no key must fail rather than silently use an ambient key.
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        asyncio.run(enrich_with_descriptions([_code()], _TITLE, api_key=""))
