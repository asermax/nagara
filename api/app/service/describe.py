"""The Gemini describer: one generated sentence per block, for a listener who cannot see it.

This module carries the describer itself (the code path uses it here; the image path reuses
`describe`) and the code-block fan-out that floors, caps, and fails per the quest. It calls
`gemini-3.5-flash-lite` directly on Google's paid API, never through a gateway.
"""

import asyncio
import json
from collections.abc import Sequence

import httpx
import stamina
from google import genai
from google.genai import types
from google.genai.errors import APIError

from ..config import settings
from ..schemas.items import CodeUnit, Unit
from .extract import sanitize_spoken

MODEL = "gemini-3.5-flash-lite"
# The documented fallback: same prompt, available when 3.5 is not. It still misidentifies
# kind on some blocks, which the quest records rather than fixes.
FALLBACK_MODEL = "gemini-3.1-flash-lite"

# The shape is carried by the config, never duplicated in the prompt: Gemini's own docs warn
# that repeating the schema (or JSON examples) in the prompt lowers output quality.
_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"spoken": {"type": "string"}},
    "required": ["spoken"],
}

# The floor a code unit reaches when the describer fails or the per-item cap is spent. It is
# a valid spoken form, so the read-along window always exists and the code stays in display.
_CODE_FLOOR = "Code with no description."

# 429 and 408 mean unlucky; 5xx means the far side is briefly down. Everything else in the 4xx
# range (400/401/403/404) means the call itself is wrong, so retrying only wastes the budget.
_RETRY_STATUS = frozenset({408, 429})


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, APIError):
        return exc.code in _RETRY_STATUS or exc.code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


@stamina.retry(on=_is_transient, attempts=3)
async def _generate(
    client: genai.Client, model: str, contents: types.ContentListUnion
) -> str:
    """One structured-output call, retried in place on a transient error by the decorator.

    google-genai does not retry on its own (its default stop is one attempt), so stamina owns
    the whole retry policy: ~3 attempts with exponential backoff and jitter, classified by
    `_is_transient`. A non-transient status raises straight through the decorator to the caller.
    This is the single call site, so a cost write point drops in here where the response lives.
    """
    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )
    text = response.text
    if not text:
        # An empty body is not a transient network fact, so it must not retry; raise a plain
        # error the fan-out catches as this unit's failure.
        raise ValueError("describe: empty response body")
    return text


async def describe(
    client: genai.Client, contents: types.ContentListUnion, *, model: str = MODEL
) -> str:
    """Call Gemini with structured output and return the sanitized spoken sentence.

    Reusable across describe paths: the caller owns `contents` — a prompt string for the code
    path here, or a prompt plus an inline image part for the image path that reuses this. The
    parsed `spoken` value runs through the same sanitize tail article prose does, because
    structured output makes the heading-and-preamble class impossible but cannot forbid a marker
    inside the string value.
    """
    parsed = json.loads(await _generate(client, model, contents))
    return sanitize_spoken(parsed["spoken"])


def build_code_prompt(title: str | None, intro: str | None, code: str) -> str:
    """Build the code describer's prompt: kind and what-for, no opener, minimal context.

    The context is asymmetric on purpose — the article title, the introducing paragraph (the
    unit just before, which the listener heard seconds ago as authority), and the block. The
    paragraph *after* is dropped: it is the elaboration the listener is about to hear anyway,
    and including it nudges the model toward describing behaviour.
    """
    return _PROMPT_TEMPLATE.format(
        title=title or "(untitled)",
        intro=intro or "(none)",
        code=code,
    )


# No opener by instruction as well as by construction: forbidding "This block"/"This example"
# left a residual "This is a…", so "This" is forbidden outright and the sentence must begin
# with the kind-noun. The invention guard is a sharpened positive instruction with no few-shot:
# kind and what-for, the introducing text as the authority, never the mechanics.
_PROMPT_TEMPLATE = """\
You are describing a code block from a technical article for someone listening to the article \
who cannot see the code.

Write exactly ONE sentence that names what KIND of code the block is and what it is FOR.

Rules:
- Begin the sentence with the kind itself, for example "A Python function", "A shell command", \
"An HTTP request", or "The syntax for". Never begin with "This", "These", "The following", or \
any preamble, and never use the word "This" anywhere in the sentence.
- Name only the kind and the purpose. Do not describe what the code does, its mechanics, its \
return values, or the framework it uses, unless the introducing text below states them.
- Treat the introducing text as the authority for what the block is about. Do not invent \
details the introducing text and the block do not support.
- Do not read the code aloud, not even a one-line block.

Article title: {title}

Introducing text: {intro}

Code block:
{code}"""


async def enrich_with_descriptions(
    units: Sequence[Unit],
    title: str | None,
    *,
    api_key: str,
    max_describes: int | None = None,
    concurrency: int | None = None,
) -> tuple[list[Unit], list[dict]]:
    """Replace each code unit's spoken form with `Code: <one generated sentence>`.

    Returns `(units, degradations)`. Units resolve independently through
    `asyncio.gather(return_exceptions=True)`, so one failed call never discards the rest. A
    failed describe floors its unit to the code floor and records a `describe failed`
    degradation; a unit past the per-item cap floors the same way with a `describe cap reached`
    degradation, in document order. The cap counts describe *invocations*, one combined budget
    the image path shares.

    Raises when there are code units and every describe attempt failed: a zero-description item
    marked complete is a silent total failure, so that case is an outage the item fails on, not
    an article state. The floor path never raises — it degrades.
    """
    result = list(units)
    code_indices = [i for i, unit in enumerate(result) if isinstance(unit, CodeUnit)]

    if not code_indices:
        return result, []

    max_describes = settings.describe_max_per_item if max_describes is None else max_describes
    concurrency = settings.describe_concurrency if concurrency is None else concurrency

    within_cap = code_indices[:max_describes]
    beyond_cap = code_indices[max_describes:]

    degradations: list[dict] = []

    for i in beyond_cap:
        result[i] = _floored(result[i])
        degradations.append({"type": "code", "reason": "describe cap reached"})

    if not within_cap:
        return result, degradations

    if not api_key:
        # Never build the client from an empty key: google-genai would fall back to the
        # ambient GOOGLE_API_KEY / GEMINI_API_KEY and a missing setting could silently
        # succeed on a developer's machine and fail in production. Fail loudly instead.
        raise RuntimeError("describe: NAGARA_GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    semaphore = asyncio.Semaphore(concurrency)

    async def describe_one(index: int) -> str:
        async with semaphore:
            prompt = build_code_prompt(
                title,
                result[index - 1].spoken if index > 0 else None,
                _code_content(result[index]),
            )
            return await describe(client, prompt)

    outcomes = await asyncio.gather(
        *(describe_one(i) for i in within_cap),
        return_exceptions=True,
    )

    resolved = 0
    for index, outcome in zip(within_cap, outcomes):
        if isinstance(outcome, BaseException):
            result[index] = _floored(result[index])
            degradations.append({"type": "code", "reason": "describe failed"})
        else:
            result[index] = result[index].model_copy(update={"spoken": f"Code: {outcome}"})
            resolved += 1

    if resolved == 0:
        raise RuntimeError("describe: every code unit failed")

    return result, degradations


def _floored(unit: Unit) -> Unit:
    return unit.model_copy(update={"spoken": _CODE_FLOOR})


def _code_content(unit: Unit) -> str:
    """The code the describer reads: the fenced block's interior, fences stripped. A block
    without fences (already prose-classified elsewhere) passes through as-is."""
    lines = unit.display.split("\n")
    if len(lines) >= 2 and lines[0].lstrip().startswith(("```", "~~~")):
        return "\n".join(lines[1:-1])
    return unit.display
