---
title: "Richer extraction groundwork"
tags:
  - adventure
summary: "Twenty-one design quests that worked out how to build richer extraction, and overturned the premise it started from."
status: done
kind: journey
priority: 1-now
created: "2026-07-31"
---

# Richer extraction groundwork

## Destination

Know how to build richer extraction well enough to slice it: what fetches a page a plain fetch cannot reach, where an article's images live once nagara owns them, what a listener hears for an image and for a code block, and what shape carries all three through the pipeline.

Reaching the end meant no trial left standing and no question a build session would have to stop and answer. It was reached on 2026-08-02, and [[richer-extraction]] is the raid that followed.

> [!warning] This journey's quests were worked outside the vault, and cannot be opened
> All twenty-one lived in `.scratch/richer-extraction/issues/`, which is gitignored and disposable. [Solved](#solved) names their origin rather than pointing at anything durable. The decisions they settled are in [[richer-extraction]]'s implementation decisions, which is the one place they survive, and which is why that raid carries its design against the quest log's usual rule.

## Bearings

**The ground.** The `api/` extraction seam, what a listener hears, and what an item's JSON exposes. Nothing in `tts/`; `web/` did not exist.

**Read first.** [[article-extraction]], [[item-contract]], [[item-lifecycle]], [[invariants]].

**Standing preferences.** Two verification habits came out of this journey and carry into everything after it. A green pipeline is not evidence the item is the article, because a 200-status error page extracts cleanly and reaches `ready`. And a strip regression is invisible in a diff and inaudible in a test summary, so a spoken form is only ever confirmed by playing it.

## Trials

**None left.** Every trial graduated into a design quest and every one of those is solved, which is what made the raid takeable.

## Solved

Twenty-one design quests, worked between 2026-07-31 and 2026-08-02. **That tree is gitignored and disposable**, so these lines name provenance rather than pointing somewhere durable; the decisions themselves are in [[richer-extraction]]'s implementation decisions.

- **01, survey cheap describer models** — one model serves both halves; DeepSeek is out because its hosted API is text-only. Ranked on documentation only, and its winner was overturned by 16.
- **02, provision firecrawl access** — Free plan, 1,000 credits, 10 req/min, 2 concurrent. A scrape bills 1 credit, enhanced bills 5, and enhanced is not plan-gated. The response carries `contentType`, per-call `creditsUsed`, and a default-on cache. **An X URL bills 30 credits while reporting `proxyUsed: basic`**, so credit cost is not predictable from proxy mode.
- **03, firecrawl markdown fidelity** — overturned the journey's founding premise. Firecrawl carries page chrome into every document and collapses `paulgraham.com` to two units. Also established that trafilatura's image loss is fatal, that firecrawl's output is non-deterministic at a 5x spread, and that no fence in either path carries a language tag.
- **13, assemble the article corpus** — ten live URLs. A 200-status error page needs no hunting, since paywalls and JS shells produce one by default.
- **09, the queued lifecycle and the retry contract** — the four-state machine, `queued_at` and `enriched_at`, the five-minute ceiling, retry on `failed` only, and invariant 5's mortality clause.
- **16, describer bake-off** — `gemini-3.5-flash-lite` wins, a candidate the quest did not name. Haiku costs 5.1x more per image. Alt feeds the prompt rather than replacing it. Nobody listened to any of it.
- **19, the emphasis glue is trafilatura's** — trafilatura discards the whitespace after an inline element in every output format, so there is nothing to escape to. 29 losses, 25 already caught, and the 4 that reach a listener are code-span and link boundaries.
- **20, an unbalanced fence swallows the article** — two independent causes needing two different fixes, and it re-scoped quest 04 by removing a poisoned test case.
- **17, where article images come from** — the image half survives. DOM containment plus `og:image`, zero false positives on the two hardest corpus entries.
- **18, non-determinism and the fallback trigger** — most of the problem was a misconfigured plain fetch. Protocol facts plus a 250-word floor, and more-spoken-words-wins. Also measured that **no shape-based plausibility test separates the corpus**, which is the first real evidence [[trustworthy-extraction]] has had.
- **11, the cassette approach** — vcrpy behind pytest-recording, and three load-bearing one-liners. Record/replay is reaffirmed rather than inherited: the "catches drift" argument weakened only for response content, and "exercises the production code path" is now the load-bearing half.
- **12, what one article costs** — a typical article is ~$0.009, about 89% of it TTS. The lever with teeth is a per-item describer cap. Quota is a firecrawl-credit problem and routes to [[api-hardening]]. Corrected after the fact; see [[richer-extraction]]'s further notes.
- **07, image storage and failure** — a shared base class, content-hash keying, a read-time-mint route, decode-validate, WebP, SVG rasterisation, and drop-the-unit on acquisition failure.
- **05, what an image unit says** — the five-step precedence, and caption extraction becoming load-bearing and per-CMS.
- **14, enrichment concurrency** — `asyncio.gather` and the whole API going async with it, two semaphores, `stamina`, and the five-minute ceiling recomputed and confirmed.
- **04, what a code unit says** — one sentence, what it is *for* and what *kind*, never what it *does*. Never dropped.
- **08, describer cost and caching** — no describer cache, firecrawl's cache left on, a per-item describer cap, a retry-count cap, and the `CostEntry` ledger.
- **15, what the extraction error surface becomes** — the `degradations` column, the hard-versus-degraded line, and six error prefixes with `fetch:` split out of `extraction:`.
- **06, the typed unit contract** — the discriminated union, the full rename, and the reversal that kept invariant 1's first clause.
- **10, migration and rollout** — transform in place, five stranded rows deleted, casing normalized, and the three-release sequence. Every decision made against production rather than against the dev database, which disagrees.
- **21, describer prompt design** — structured output plus sanitize, one prompt per kind, and **the first quest in the journey to put output through the production TTS path and hear it**.

## Out of scope

**Building any of it.** A journey clears ground and holds no build quest. Everything the twenty-one settled is landed by [[richer-extraction]].

**Whether the item is the right article.** The corpus work produced the first real evidence on it and handed that to [[trustworthy-extraction]], which stays open and adjacent rather than being absorbed here.

## Outcome

**The ground was cleared, and the premise did not survive it.** Firecrawl was going to replace trafilatura outright; quest 03 measured that it cannot, and the answer became a fallback fetch with trafilatura keeping the extraction and exactly one segmentation. Everything downstream was designed against that reversal rather than the original plan.

Two spike branches carry this journey's evidence and are never merged: `idea/firecrawl-markdown-fidelity` (the corpus cache, the cost model, the bake-off, the image and boundary prototypes) and `idea/describer-prompt-design` (the prompt variants and the sixteen listen clips). Both are inherited by [[richer-extraction]] and struck by it, along with `.scratch/richer-extraction/`. `idea/firecrawl-as-the-extractor` is a separate experiment and not this journey's.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[trustworthy-extraction]] · [[api-hardening]]
