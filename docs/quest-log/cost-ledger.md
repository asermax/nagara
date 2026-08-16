---
title: "The cost ledger"
tags:
  - quest
summary: "A CostEntry row per firecrawl, describer and TTS call, carrying both the raw measure and the dollar cost snapshotted at call time."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 2-soon
created: "2026-08-02"
---

# The cost ledger

## What

Enqueue used to be free. It now spends firecrawl credits and, once the describer lands, model calls, and with the work moved off the request there is no way to see what an item cost.

One row per metered event, scoped to its item.

This records spend. It does not enforce anything, and it does not expose anything: a cost-reading endpoint is a new route and out of [[richer-extraction]]'s scope.

## Design

### The table

`cost_entries`, one row per event, each scoped to an `item_id`:

| Column | Holds |
|---|---|
| `type` | a constant map, not an enum: `firecrawl` / `describer` / `tts` |
| `quantity` + `unit` | the raw measure: credits, calls, or seconds |
| `dollars` | the cost snapshotted at call time |
| `detail` | JSON, nullable, for type-specific extras |

`detail` carries the firecrawl destination and proxy, whether a describer call was for an image or for code, and the TTS duration. That last one is what lets you ask "image against code describer calls" later and tune the cap on evidence.

> [!note] Why both the raw measure and the dollars
> The raw measure never goes stale and lets you re-price against future rates. The dollar snapshot gives instant totals without a price-table join. Keeping only one of them loses one of those.

A ledger beats two aggregate columns on the item: cost is its own domain, the table generalizes to TTS rather than covering only the new spend, and per-event rows answer questions aggregates cannot.

### Prices come from configuration

A small price surface the enrichment and TTS paths read to snapshot dollars: firecrawl dollars-per-credit, which is plan-tier dependent, and the Gemini per-call rate. Snapshotted at write, never recomputed.

### Write points

Firecrawl reports `creditsUsed` per response, so spend is measured rather than modelled. TTS bills on duration. The describer's write point arrives with [[describe-code-blocks]].

### What the numbers say today

A typical article is roughly **$0.009, about 89% of it TTS**. The describer adds fractions of a cent. The corpus worst case is a code-heavy tutorial, and an X URL is 13x baseline entirely from the 30-credit fetch, where describer levers are irrelevant.

> [!warning] Every describer figure in the cost model is a ceiling, and one figure points the other way
> The model was built before three sibling quests landed and was corrected after: roughly three of the code-heavy article's "code" units were prose that [[fence-segmentation-repair]] re-classifies, a good caption or alt now skips the describer entirely, and production calls Gemini directly rather than through a gateway.
>
> The correction pointing the other way is the largest. **TTS is modelled flat at $0.008 per article**, which hides the ~3,687 words the fence fix recovers on that same article: roughly $0.012 more, putting its real total near $0.045. **Re-derive TTS per word before trusting any code-heavy row.**

### What this is not

The exposure that is real at nagara's volume is **firecrawl credits, not describer dollars**. A queue that is 2% X URLs burns roughly 6,000 credits a month at 10,000 articles, breaching Free and Hobby. That is [[api-hardening]]'s to enforce, and this quest only makes it visible.

### How it is verified

Seam 1. Enqueue an escalating URL and assert a `firecrawl` entry exists with the credits the cassette reported and a dollar figure derived from configured prices. Assert a `tts` entry on a completed item. Nothing here asserts a total against a hardcoded number, because prices are configuration.

## Answer

Built on branch `raid/cost-ledger`, merged to `main` as `2be3811`. A `cost_entries` table holds one row per metered event scoped to `item_id`, carrying both the raw measure (`quantity` + `unit`) and `dollars` snapshotted from configured prices at write time. `type` is a `Literal["firecrawl","describer","tts"]` with the runtime tuple derived via `get_args`, so the two cannot drift (no enum). Migration `e5b1c9a742d0`, `down_revision = a4e7f2b91c56`.

**The write points are conditional on the credit being spent, not on the item succeeding.** firecrawl reads `creditsUsed` off the scrape response and emits through a sync capture callback the moment the scrape returns, before any thin-result early return can swallow it; the callback only captures (it runs in the threadpool), and the DB write happens back in the async context and commits on its own, so a concurrent poll's conditional write can never drop the metered fact. The firecrawl cost is recorded on both the success path and the extraction-failed path. TTS records on duration and rides the same commit that finalizes the item to `ready`.

**Left behind for integration.** The `describer` type value exists but its write point is not wired — the quest scoped it to [[describe-code-blocks]], and the raid session stitches it when that slice merges. Prices (`firecrawl_dollars_per_credit`, `gemini_dollars_per_call`, `tts_dollars_per_second`) are plan/vendor-dependent estimates on `Settings` and in `api/.env.example`; set them to the real tier.

**What would make it stop being true.** A fourth metered event kind added to `CostType` without a write point, or a firecrawl SDK that stops parsing `creditsUsed` into `metadata.credits_used`. Verified at seam 1 by replaying the existing firecrawl cassette and asserting entries with config-derived dollars, never a hardcoded total.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[firecrawl-fallback-fetch]] · [[api-hardening]] · [[pricing-model]] · [[persistence-and-storage]]
