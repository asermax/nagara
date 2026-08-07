---
title: "Reach guarded pages"
tags:
  - quest
summary: "Extract an article from a page a plain HTTP fetch can't reach: a rendering proxy and accepting pre-rendered HTML as an input are both on the table, and neither is chosen."
status: solved
kind: design
adventure: richer-extraction
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Reach guarded pages

## What

Extract an article from a page [[article-extraction]]'s plain HTTP fetch cannot reach: X/Twitter URLs fail outright because the content is JS-rendered, and Cloudflare-guarded pages answer with a `403` and a `text/plain` body instead of the article. Both sit beyond the boundary that note's "why no headless browser" callout found for ordinary articles.

The shape question this settles: which closes the gap, fetching through firecrawl or a similar rendering proxy, or accepting pre-rendered HTML as an alternative input to a bare URL? Neither is chosen. A rendering proxy adds a paid dependency to every fetch that needs it; accepting pre-rendered HTML as an input changes what nagara's enqueue call accepts at all. The cost trade-off between the two is itself part of what is unknown, not a detail to settle after picking one.

Already verified, out-of-band: a firecrawl-rendered tweet feeds the extraction pipeline fine once fetched, so the content itself is synthesizable and only the fetch step is missing.

## Answer

**Settled by building it: a rendering proxy, as a fallback rather than as the fetch.** Firecrawl scrapes the URL only when a plain fetch fails or returns too little, and trafilatura still does the extracting from its `rawHtml`, so there is one segmentation rather than two. Pre-rendered HTML as an alternative enqueue input was not taken: it changes what the API accepts for every caller to serve the minority of URLs that need it.

The cost trade-off this quest called unknown was measured before the choice. A guarded page does not bill the documented 1-or-5 credit split — an X status URL bills **30** while reporting `proxyUsed: basic` — so parity with an ordinary article was never available, and the answer is a fallback precisely because it cannot be the default path.

**How far it reaches.** Built, merged and deployed. The escalation trigger is a non-2xx, any extraction failure except the content-type gate, or fewer than 250 spoken words, and it never fails an item on its own — it only buys a second opinion. Verified against a ten-URL corpus and one recorded cassette; [[article-extraction]] is where the mechanism is described once the raid that built it writes its notes. The X case is the one this quest was written for and is the most expensive one that works.

**What would make it stop being true.** A destination firecrawl itself cannot render, or the free plan's 1,000 credits becoming binding — at 30 credits an X fetch, that is about 33 such pages a month, which routes to [[api-hardening]] rather than back here.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]]
