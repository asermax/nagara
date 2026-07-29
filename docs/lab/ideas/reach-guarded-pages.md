---
title: "Reach guarded pages"
tags:
  - idea
summary: "Extract an article from a page a plain HTTP fetch can't reach: a rendering proxy and accepting pre-rendered HTML as an input are both on the table, and neither is chosen."
status: shaped
priority: soon
impact: medium
size: medium
experiments:
---

# Reach guarded pages

## Objective

Extract an article from a page [[article-extraction]]'s plain HTTP fetch cannot reach: X/Twitter URLs fail outright because the content is JS-rendered, and Cloudflare-guarded pages answer with a `403` and a `text/plain` body instead of the article. Both sit beyond the boundary that note's "why no headless browser" callout found for ordinary articles.

Already verified, out-of-band: a firecrawl-rendered tweet feeds the extraction pipeline fine once fetched, so the content itself is synthesizable and only the fetch step is missing.

## Unknowns

- Which shape closes the gap: fetching through firecrawl or a similar rendering proxy, or accepting pre-rendered HTML as an alternative input to a bare URL? Neither is chosen. A rendering proxy adds a paid dependency to every fetch that needs it; accepting pre-rendered HTML as an input changes what nagara's enqueue call accepts at all. The cost trade-off between the two is itself part of what is unknown, not a detail to settle after picking one.

---

Related: [[lab/README|the lab]] · [[article-extraction]]
