---
title: "LLM extraction pipeline"
tags:
  - adventure
summary: "Replace the extraction pipeline with firecrawl always, HTML always, and an LLM instead of trafilatura deciding what to extract, with an eval system for the prompt."
status: open
kind: journey
priority: 1-now
created: "2026-08-31"
---

# LLM extraction pipeline

## Destination

Knowing how to replace the current extraction pipeline with one that **always uses firecrawl**, **always extracts HTML directly**, and has **an LLM identify and extract the article's main body, paragraphs, images and so on instead of trafilatura**. The rest of the pipeline stays as it is.

The point is better coverage from always going through firecrawl, and using an LLM as the mechanism for figuring out what to extract from a page, ideally getting rid of all the custom logic handling edge cases by dumping that on the LLM. The LLM is also responsible for detecting footnotes and other undesired stuff from the article.

Reaching the end also means knowing how an **eval system for the LLM prompt** works, and how the LLM is **included in the cost calculation**.

## Bearings

**The ground.** The extraction pipeline in `api/`: the fetch layer, the trafilatura segmentation, and the custom edge-case handling around it. The rest of the pipeline (synthesis, timing, the item contract, delivery) stays as is.

**Read first.** [[article-extraction]] for how extraction works today, including the plain-fetch-then-firecrawl escalation, the footnote pruning, the cruft trim and the image enrichment. [[persistence-and-storage]] for how costs are metered today (`firecrawl` / `describer` / `tts`). [[invariants]] for invariant 1, one extraction as the source of truth, and invariant 2, one typed unit list.

Note that [[article-extraction]] carries a `> [!info]` callout rejecting **firecrawl's own markdown** as the extractor, which is a different proposal from this one: this journey keeps firecrawl as the fetch and puts an LLM over the HTML.

**Standing preferences.** Keep the rest of the pipeline as is.

## Trials

- What the LLM returns and how it lands on the existing typed unit list.
- Which of the custom edge-case handling goes away, and whether all of it can.
- How the LLM detects footnotes and the other undesired stuff.
- What an eval system for the prompt looks like.
- How the LLM lands in the cost calculation.

## Solved

Nothing yet.

## Out of scope

Anything past extraction: synthesis, timing, the item contract and delivery stay as they are.

---

Related: [[quest-log/README|the quest log]]
