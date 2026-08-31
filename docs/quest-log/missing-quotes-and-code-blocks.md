---
title: "Missing quotes and code blocks"
tags:
  - quest
summary: "Quoted text and code blocks are missing from some listen articles; find out whether it is fetch-side or parse-side."
status: solved
kind: spike
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# Missing quotes and code blocks

## What

Quoted text and code blocks are missing from some listen articles, e.g. Armin's "What is Reasoning?". Need to check if it's a fetch issue (nagara not extracting) or parse-side (our build dropping them). Data point: the extensible-software nagara response DID include `code` type units (13), so code extraction works there — suspicion: fetch-side issue or markdown blockquote handling.

## Answer

**Fetch-side.** Both halves die inside `trafilatura.extract`, before a single character of markdown exists, so `units_from_markdown` never has the chance to drop them. Two distinct mechanisms, one per half.

### Code blocks: `favor_precision=True` prunes them out of trafilatura's own tree

`What Is Reasoning` (https://lucumr.pocoo.org/2026/8/19/what-is-reasoning/) carries three `<pre>` blocks. Diffing trafilatura's **own XML output** with the flag on and off, everything else nagara's config, all three are simply absent under `favor_precision=True` while the six inline `<code>` spans survive:

| `favor_precision` | `<code>` in trafilatura's XML | markdown fence lines | words |
|---|---|---|---|
| `True` (nagara's) | 6 (all inline) | 0 | 551 |
| `False` | 9 | 6 | 612 |

The 61-word delta is exactly the three blocks. `include_formatting` is not a second lever (off/on gives the same result either way), and it is not trafilatura's external-extractor comparison either: `fast=True`, which disables that comparison entirely, changes nothing.

What a listener gets is the sharp part. The prose that *introduces* each block survives, so the audio runs "GPT-OSS's Harmony response format makes this easy to see:" straight into the next paragraph. Three announced quotations, three silences. That is why this presents as *quoted text* missing rather than as code missing: what Armin quotes is model output and prompt text, and his blog renders those as `<pre>`. Both halves of the complaint against this article are the same three blocks.

Nothing catches it. The item reaches `ready`, 13 units, no `failed`, no degradation recorded, and 551 spoken words clears the 250-word firecrawl floor by 2x, so the fallback fetch never escalates. This is [[trustworthy-extraction]]'s failure mode: a green pipeline that is not the article.

> This is **not** a blanket property of `favor_precision`. `t17_realpython.html` has 80 `<pre>` and keeps all of them (149 fence lines) with the flag on. Whatever the flag is reacting to here, it is conditional, and the fix quest has to find that condition rather than assume the flag is the whole story.

### Blockquotes: trafilatura recognises them and its markdown writer has no rule for them

The article contains **zero** `<blockquote>` — no `<q>`, no quote-classed element either — so it cannot answer this half. Per [[quest-log/README|the quest log]]'s pre-registered-probe rule, a minimal synthetic page reaches the case, marked **probe, not artifact**:

trafilatura *does* recognise the blockquote: its XML output carries `<quote><p>A quoted claim…</p></quote>`. Its markdown writer then drops it. `replace_element_text` in `trafilatura/xml.py` branches on `head`, `del`, `hi`, `code`, `ref` and `cell`; there is no `quote` branch, so a recognised `<quote>` renders as its children's bare text with no `>` marker, in every output format.

So the quote's **text is never lost** — it is read aloud. What is lost is its quote-ness: it arrives as an ordinary `paragraph` unit, indistinguishable from surrounding prose in both `display` and `spoken`.

The corollary matters more than the probe. `_split_units`' blockquote branch (`api/app/service/extract.py`) keeps a `>`-prefixed block whole as one unit, and **it cannot fire on trafilatura-extracted markdown**, because trafilatura never emits `>`. Confirmed on real data, not only the probe: across all four `api/tests/fixtures/*.html` plus this article, zero markdown blockquote lines, including `t17_newyorker.html`, which has a real `<blockquote>` in source.

### How far this reaches, and what would make it stop being true

One article, one machine, one cached fetch, on the versions pinned in `api/uv.lock`. The verdict — fetch-side, not parse-side — is owned by that article; the blockquote half is owned by the synthetic probe and covers the extract + segmentation path only, saying nothing about audio and nothing about frequency.

It stops being true if trafilatura changes its precision pruning or adds a `quote` branch to its markdown writer (both are upstream-version-sensitive, so re-run `spike/xml_diff.py` and `spike/quote_marker.py` after a bump), or if the cached HTML goes stale against the live page.

**Observation, not measured here:** the blockquote mechanism is structural in trafilatura's writer, so it should hold for every article nagara extracts, not just this one. How widespread the `<pre>` pruning is was deliberately not checked — `extensible-software` stays the cited contrast data point it already was, unre-fetched. Both belong to a follow-up quest, alongside the fix itself.

### Left in the worktree

Branch `idea/missing-quotes-and-code-blocks`, never merged. `spike/`, with `spike/README.md` naming the one command per script, `spike/cache/what-is-reasoning.html` as the cached artifact, and `spike/xml_diff.py` as the decisive one. Nothing under `api/`, `tts/` or `docs/` was touched beyond this record; `uv run pytest` (206 passed), `ruff check` and `ty check` are green in `api/`.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[what-gets-read-aloud]]
