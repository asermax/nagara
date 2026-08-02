---
title: "Firecrawl as a fallback fetch"
tags:
  - quest
summary: "When a plain fetch fails or returns too little, firecrawl scrapes the same URL and trafilatura extracts from its rawHtml; more spoken words wins."
status: open
kind: build
adventure: richer-extraction
blocked_by:
  - plain-fetch-hardening
  - queued-item-lifecycle
priority: 2-soon
created: "2026-08-02"
---

# Firecrawl as a fallback fetch

## What

Enqueue an X post or a Cloudflare-challenged page and get audio. Those pages return 200 with a JS shell today, so nothing about the response says it failed and nothing usable comes out.

A plain fetch still runs first and still does the extracting. Firecrawl fetches and converts; it does not find the article. This closes [[reach-guarded-pages]].

> [!warning] The premise this quest started from was overturned by measurement
> Firecrawl was going to replace trafilatura outright. It cannot: its markdown carries page chrome into every document, "Skip to main content" and "Save this story" twice and sponsor blocks, and it collapses `paulgraham.com` from 72 KB to two units because it preserves table-based layout. `only_main_content` is already on by default and changes nothing. The original objection to a fallback, that it would create two segmentation paths, only applied when firecrawl was doing the segmenting.

## Design

### The escalation trigger

Escalate when any of these holds:

1. `response.status` is not 2xx.
2. Any of four `ExtractionError` raise sites fires: fetch failed, could not decode, no article text, no units.
3. The extraction yields fewer than **250 spoken words**.

The content-type gate does **not** escalate. A PDF is a clean failure and firecrawl will not make it HTML, so that branch keeps raising.

No condition here ever fails an item on its own. Each one only buys a second opinion, and the floor in particular is a get-a-second-opinion signal rather than a verdict.

The floor comes from a corpus with a canyon in it rather than a boundary: the broken X extraction is 37 spoken words and the smallest legitimate article is 1,002. The gap is 27x, which is why the trigger is stable and an item cannot flap between escalating and not.

> [!note] The corpus contains no genuinely short article, so 250 is safe on what exists and untested on what does not
> The real risk is a 300-word post. That risk is bounded by the floor never failing anything on its own.

### What firecrawl is called with

`formats=["rawHtml", "markdown"]`, `proxy="auto"`, and `maxAge` **omitted**.

**`rawHtml` feeds trafilatura**, exactly as a plain fetch's HTML does, so there is one `trafilatura.extract` call site and one segmentation. Invariant 1 holds by construction rather than by argument.

Trafilatura's prose output is byte-identical from `rawHtml` and from firecrawl's cleaned `html` (19,820 against 19,820 on the New Yorker, 3,103 against 3,103 on Wired). So `only_main_content` is invisible to the prose, and `rawHtml` is chosen for the images the cleaning throws away: 9 against 5 on the New Yorker. [[article-image-units]] is the consumer of that difference.

**`markdown` rides along at the same credit** and is evidence rather than pipeline input.

**`proxy="auto"`** bills 1 credit when basic suffices and 5 only when it escalates to stealth. Hardcoding `basic` fails on genuinely guarded pages; hardcoding `stealth` always bills 5. Note the naming trap: the request-side name is `enhanced` and the response reports `proxyUsed: "stealth"`, so grepping for one term misses the other.

**`maxAge` is omitted**, taking firecrawl's 2-day default, and this is the reverse of what the cost work expected. Firecrawl caches by default and serves hits without being asked, while still billing full price, so suppressing the cache saves nothing. What it trades is freshness, capped at two days. Firecrawl's own docs say `maxAge: 0` is more likely to fail, and it runs only on pages a plain fetch could not reach, where a cached success beats a forced fresh attempt.

### Choosing between the two extractions

**More spoken words wins.** Correct on every corpus entry, including the two that pull opposite ways:

| | plain | firecrawl | picked |
|---|---|---|---|
| mitchellh, before the user-agent fix | 2 units / 8 words | 53 / 2,281 | firecrawl |
| wired | 61 / 3,912 | 36 / 517 | plain |
| stackoverflow | 403, nothing | 61 / 639 | firecrawl |
| acx, realpython | identical | identical | tie |

The trap worth naming: firecrawl's `rawHtml` is post-JavaScript, so it can contain hydrated chrome a plain fetch never had, and a longer-wins rule could in principle prefer that garbage. It does not happen on this corpus. Firecrawl's output deflates rather than inflates, most sharply on Wired where it returns an eighth of the article the plain fetch already had.

### Non-determinism, and where it actually bites

Measured on the same URL with the same arguments, minutes apart: 11,422 / 55,366 / 11,608 characters, 13 / 49 / 13 images. A 5x spread.

**A bad response is detectable by comparison, and that is better than any absolute test.** The plain fetch always runs first, so there is nearly always a baseline. The spread only matters where nothing can check it.

**Where there is no baseline, accept whatever comes back.** No floor applies on that path and the item is never failed for being small. `proxy="auto"` is what buys the best chance of real content there. On the corpus this is 1 URL in 10.

> [!note] This is deliberately the permissive choice on the one path with no safety net
> The alternative, sampling firecrawl twice for a synthetic baseline, costs double exactly where calls are most expensive: an X-shaped URL at 30 credits becomes 60, to defend a case that is 10% of escalations, which are themselves a minority of enqueues.

### Configuration and cost

`NAGARA_FIRECRAWL_API_KEY` on `Settings`, read with the existing `NAGARA_` prefix. The SDK reads a bare `FIRECRAWL_API_KEY` from the environment when no `api_key` argument is passed; **pass it explicitly from settings anyway**, because ambient lookup would put the one credential outside the object every other credential goes through, and the ambient name does not match the project's prefix regardless.

The account is on Free: 1,000 credits per billing period, 10 scrape requests per minute, 2 concurrent. Those limits are one call per item, so they bound items in flight rather than units within one enrichment.

> [!warning] A guarded page is far worse than the documented 5x, and the multiplier is not predictable from proxy mode
> Measured: `example.com` bills 1, `paulgraham.com` at 72 KB bills 1, `example.com` forced to enhanced bills 5, and **an X status URL bills 30 while reporting `proxyUsed: "basic"`**. Some destinations carry their own multiplier regardless of how they were fetched, so any cost model assuming a 1-or-5 split is wrong. At 30 credits the free plan is about 33 such fetches a month.

The firecrawl-credit ceiling and per-destination enforcement belong to [[api-hardening]], not here. This quest spends credits; it does not police them.

> [!warning] `railway.toml` carries no environment variables at all
> Every secret is a Railway dashboard variable. Set the firecrawl key there **before** the merge that needs it, or `preDeployCommand` runs the migration, the new code boots, and every escalating enqueue fails on a missing key.

`api/.env.example` does not exist and is owed by this build, covering every setting rather than only the new one.

### The sixth error prefix

`enrichment:` joins the five [[plain-fetch-hardening]] settled. Firecrawl-unreachable is **`fetch:`**, not `enrichment:`, because the prefix names the pipeline phase rather than the background-task block, and firecrawl is a fetch.

One wrinkle is accepted: a firecrawl call that *errors* reports `fetch: firecrawl unreachable`, while one that *hangs* is caught by the five-minute ceiling and reports `enrichment: no result after 300s`. The ceiling cannot tell which sub-phase it is stuck in, and teaching it is not worth the bookkeeping.

Firecrawl is not content-type gated at all. It runs only on escalation, which requires the plain fetch to have passed the HTML gate, so a PDF is caught before firecrawl ever sees one. If firecrawl returned non-HTML anyway, trafilatura extracts nothing and more-words-wins keeps the plain extraction. `metadata.contentType` rides along as evidence and is ignored for gating.

### How it is verified

Seam 1, the HTTP surface, with cassettes.

**Most escalation tests need no firecrawl fixture at all.** The trigger is protocol facts, so a recorded non-2xx drives the escalation, and more-spoken-words-wins is a pure function of two extractions testable with no network on either side.

Where a firecrawl cassette is genuinely needed, the discipline is fixed by the non-determinism: **assert on the code path and the response schema, never on unit counts.** Counts come from the recorded corpus baseline. Replay is deterministic because a cassette returns its recorded bytes verbatim; the 5x spread bites re-record, never replay. The no-baseline path replays one representative sample and asserts nothing about its size, matching the runtime decision.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[reach-guarded-pages]] · [[plain-fetch-hardening]] · [[queued-item-lifecycle]] · [[article-extraction]] · [[api-hardening]] · [[trustworthy-extraction]]
