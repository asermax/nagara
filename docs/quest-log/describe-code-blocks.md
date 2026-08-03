---
title: "Describe code blocks"
tags:
  - quest
summary: "One generated sentence per code block saying what it is for and what kind it is, replacing the literal string \"Code sample.\""
status: open
kind: build
adventure: richer-extraction
blocked_by: []
priority: 3-later
created: "2026-08-02"
---

# Describe code blocks

## What

`_to_spoken` turns every fenced block into the string `"Code sample."` It is honest and useless: a listener learns a code block exists and nothing about it.

Enqueue `simonwillison.net` and hear `Code: A Python function that…` instead.

This quest carries the describer itself, because a model client with no caller is not demoable. [[describe-article-images]] then reuses it.

It is blocked by [[fence-segmentation-repair]] for a hard reason: without that fix the describer is pointed at units that are mostly article prose, and it will summarise an essay and call it a code sample.

## Design

### The target: what it is FOR, never what it DOES

One sentence naming what *kind* of code the block is and what it is *for*. Never a readback of the code, one-liners included. Never a claim about what it *does*: the mechanics, the return type, the framework. That is precisely the invention surface, and a listener doing something else cannot check it against code they cannot see.

Code has no attached authorial text, so the closest thing is the **introducing prose**, the unit immediately before, which the listener heard as its own window seconds ago. That is treated as authoritative.

> [!note] The corpus finding that set the question
> This was designed imagining "a subtle algorithm" as the stress case. The corpus has none: the code-heavy article carries ~71 genuine blocks at a median of 5 lines, and the largest genuine block is a ~21-line REPL arithmetic transcript. In **every one** of the five baked-off genuine blocks the introducing unit already named the block, and the model restated it. The describer is not surfacing a hidden algorithm; it is naming the kind and seconding the introducing sentence.

### Six decisions

| # | Decision |
|---|---|
| 1 | Never read the code aloud, one-liners included |
| 2 | Always generate one sentence per block; the redundancy with the introducing prose is the price of the code's own audio window |
| 3 | One sentence, fixed, not proportional to block size |
| 4 | `Code: ` prefix, and the describer outputs no self-opener |
| 5 | Never dropped; describer failure or cap exhaustion falls to `Code with no description.` |
| 6 | No language-tag branching; the describer infers it and folds it into the kind-name |

**On the redundancy (2).** What the describer adds above restatement is the *kind* and the *structure*: "the syntax for creating a variable" names the concept, an MCP tool list gets enumerated, an HTTP request's shape gets named. Naming the kind is low-invention signal and is the value above the floor. The parts that would add most, specific field names and query values, are exactly the invention surface, which is why the prompt constrains to kind rather than behaviour. The cost tail is real and is bounded by the cap below, not by declining to generate.

**On never dropping (5).** Unlike an image, a code block is already extracted text, so **there is no acquisition-failure path**. The only ways a code unit lacks a description are describer failure and cap exhaustion, and both fall to the same floor, so the read-along window always exists and the code always stays in display. A snippet the preceding prose already covered still gets its own sentence, because dropping removes the code from the reader's view, and in a tutorial that is a real loss.

**On the language tag (6).** No fence in the corpus carries one, in either extraction path, so the language is always inferred. It becomes a word inside the sentence rather than a separate rule. A tag, if one ever appears, is a hint and not a branch, and it rides in the display markdown untouched.

Reading one-liners aloud was considered and rejected: `variable_name = variable_value` and `>>> from math import sqrt` read worse spoken, symbols and REPL prompts, than "the syntax for assigning a variable".

### The describer

**`gemini-3.5-flash-lite`, called directly on Google's paid API**, with `gemini-3.1-flash-lite` as the documented fallback. Both inherit the same prompt.

The bake-off ran every candidate through OpenRouter to compare them with one key; production drops the gateway, which is marginally cheaper and does not change the model's behaviour. Gemini's per-image token count is near-constant, a 1.03x spread against Haiku's 3.17x, and Haiku costs **5.1x more per image**. Flash-Lite's RPM is not binding at nagara's scale, so there is no rate-pacing machinery. DeepSeek was ruled out early because its hosted API is text-only.

**Structured output plus sanitize, both.** `response_mime_type="application/json"` with:

```
response_schema = {
    "type": "object",
    "properties": {"spoken": {"type": "string"}},
    "required": ["spoken"],
}
```

The parsed `spoken` then runs through the same belt-and-suspenders tail `_to_spoken` applies to article text. That tail is inline in `_to_spoken` today and wants extracting into a named function first: a small prefactor that makes this quest's wiring trivial.

> [!important] Both guards, because the marker leak is stochastic
> A backtick reached narration once in the bake-off and did **not** reproduce across 48 free-text re-runs. "It did not happen this time" is exactly the judgement you cannot rely on in a pipeline where a leaked marker is only ever caught by playing the audio. Structured output makes the heading-and-preamble class *impossible*; sanitize catches a marker inside the string value, which a JSON schema cannot forbid.

**The schema is not duplicated in the prompt.** Gemini's own docs warn that duplicating the schema, or JSON examples, lowers output quality. The prompt describes the task and the config carries the shape.

### The prompt

**No opener, by construction and by instruction.** The sentence must begin with the kind-noun, and the prompt forbids "This", "These", "The following", and any preamble. `Code: ` is nagara's announcement, so the model owns only the content.

> [!note] The no-opener needed two passes on code
> Every bake-off code output opened with "This block/section/output demonstrates…". Forbidding "This block" and "This example" left a residual **"This is a…"**, because the model substitutes the demonstrative it was told to drop. Forbid "This" outright and require the sentence to begin with the kind. After that pass every output opens with a kind-noun, and by ear `Code: A Python variable definition…` lands clean where `Code: This example demonstrates the basic syntax…` stuttered.

**The invention guard is a sharpened positive instruction, no few-shot.** Kind and what-for, the introducing prose as authority, never what it does: no mechanics, return values, or framework names unless the introducing prose states them.

**Context is minimal and asymmetric.** The article title, the introducing paragraph, and the content. The paragraph *after* is **dropped**: it is the elaboration the listener is about to hear anyway, and including it nudges toward behaviour description.

> [!note] The fallback model still misidentifies kind, and that is recorded rather than fixed
> Under structured output, `gemini-3.1-flash-lite` wrote "A TypeScript interface…" for a one-line JSON block. That is kind-level rather than behaviour-level, and 3.1 exists to be available when 3.5 is not rather than to match it. Free-text was marginally more accurate on that one case, which does not outweigh the structural guarantee above.

### Fan-out and its bounds

`asyncio.gather(..., return_exceptions=True)`, so every unit resolves independently and no single failure aborts the gather. A fifty-unit article where one call fails must not discard the other forty-nine, and independent resolution is the only model compatible with [[queued-item-lifecycle]]'s incremental writes and resume-from-`enriched_at`.

**`NAGARA_DESCRIBE_CONCURRENCY`, default 10.** Low-stakes: async coroutines yield on I/O and do not compete with request serving the way threads would, and RPM is not binding. Ten finishes the ~91-unit worst case in about 34 seconds.

**Transient errors retry in place with `stamina`**, a new `api` dependency: async `@stamina.retry`, roughly three attempts, exponential backoff with jitter, classifying through stamina's `on` hook. 429, 408, 5xx and connection or timeout errors retry. 400, 401, 403 and 404 fail the unit immediately, because they mean the call is wrong rather than unlucky.

**`NAGARA_DESCRIBE_MAX_PER_ITEM`, default 25.** One combined budget for code and images, counting units that reach the generator after any caption or alt precedence skips. Past the cap, units fall to their non-describer form in document order. The cap never fails an item and never goes silent.

> [!note] Why 25
> It sits just above the measured collapse point where a code-heavy article's describer spend falls back to the TTS baseline, so a ~70-block tutorial gets ~25 described and the rest floored, while still absorbing a genuinely pathological 50-image gallery. It is a setting, so the cost of being wrong is one environment variable.
>
> The source quest's heading says 50 and its body says 25 twice. 25 is what the body's reasoning derives.

**No describer cache.** Per-row resume already handles the common retry case. What is lost is cross-article dedup of the same snippet, second-order on cost, and amortization of a total-loss retry, which is an enforcement problem rather than a caching one. Defending against abuse with a cache is the wrong tool; [[retry-a-failed-item]]'s count cap is the local bound and [[api-hardening]] owns the rest.

### Systemic failure is hard, per-unit failure is degraded

`enriched_at` is set only when **every** unit has resolved. Every enrichable unit failing fails the item, because a zero-spoken item marked complete is a silent total failure and "every unit failed" is an outage rather than an article state.

A single unit failing writes a `describe failed` degradation and floors the unit.

There is no `EnrichmentError`. The gather's `return_exceptions=True` makes a per-unit failure a value in a result list and a systemic failure a condition the task checks, so an exception nobody raises would be furniture.

### Configuration

`NAGARA_GEMINI_API_KEY` on `Settings`. Set it in the **Railway dashboard before the merge**, because `railway.toml` carries no environment variables and the alternative is every enqueue failing on a missing key.

### How it is verified

Seam 1, with the model's text response cassetted. A describer cassette **asserts on the HTTP and JSON shape, never on the exact sentence**, which varies by temperature and cannot be judged from a test either way.

What can be asserted deterministically: the sanitize tail strips a marker from a recorded response that contains one, the `Code: ` prefix is applied by nagara rather than the model, the cap floors units past 25 in document order, and a recorded 400 fails the unit without retrying while a recorded 429 retries.

Whether it *sounds* right is not a test. That is [[richer-extraction-listen-pass]].

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[fence-segmentation-repair]] · [[describe-article-images]] · [[richer-extraction-listen-pass]] · [[api-hardening]]
