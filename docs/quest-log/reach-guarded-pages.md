---
title: "Reach guarded pages"
tags:
  - quest
summary: "Extract an article from a page a plain HTTP fetch can't reach: a rendering proxy and accepting pre-rendered HTML as an input are both on the table, and neither is chosen."
status: open
kind: design
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Reach guarded pages

## What

Extract an article from a page [[article-extraction]]'s plain HTTP fetch cannot reach: X/Twitter URLs fail outright because the content is JS-rendered, and Cloudflare-guarded pages answer with a `403` and a `text/plain` body instead of the article. Both sit beyond the boundary that note's "why no headless browser" callout found for ordinary articles.

The shape question this settles: which closes the gap, fetching through firecrawl or a similar rendering proxy, or accepting pre-rendered HTML as an alternative input to a bare URL? Neither is chosen. A rendering proxy adds a paid dependency to every fetch that needs it; accepting pre-rendered HTML as an input changes what nagara's enqueue call accepts at all. The cost trade-off between the two is itself part of what is unknown, not a detail to settle after picking one.

Already verified, out-of-band: a firecrawl-rendered tweet feeds the extraction pipeline fine once fetched, so the content itself is synthesizable and only the fetch step is missing.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]]
