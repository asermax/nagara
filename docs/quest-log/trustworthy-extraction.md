---
title: "Trustworthy extraction"
tags:
  - quest
summary: "Be able to trust that a ready item is actually the article it claims to be, not a 200-status error page read aloud."
status: open
kind: research
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Trustworthy extraction

## What

Be able to trust that a `ready` item is the article it claims to be. Today a URL serving an HTTP `200` error page (a GitHub Pages 404, say) extracts successfully, so the pipeline generates audio of the error page being read aloud: the worst failure mode this project has, because it looks exactly like a working item and the status is never `failed` (see [[item-lifecycle]]'s warning on this). Nothing in [[article-extraction]] catches it.

The question this settles: does a heuristic that checks the extracted paragraphs for real content (title presence, length, known error-page shapes) separate an error page from a short but legitimate article, without rejecting real content along the way? Not yet tried. This is the whole difficulty: a naive length or title check risks throwing out a real short article exactly as readily as it catches a fake one, and nobody has looked at what real error pages and real short articles actually look like side by side.

## Evidence in hand

The extraction-fidelity work gathered the first real evidence against a shape-based plausibility test, and it is discouraging. Measured across the corpus, no per-item shape separates a degraded extraction from a legitimate one:

- **Median unit length does not separate.** A degraded extraction sits at 12, between a legitimate article at 11 and another at 16.
- **Link density does not separate** either.
- **Only total word count separates**, and only because the corpus happens to contain no genuinely short article. A real 300-word post would collapse that gap, so word count is safe on what exists and untested on the case that matters.

One narrow case is already closed at the fetch layer rather than here: a browser user agent plus an HTTP status check stops the specific 403 error page (a server answering the default agent with a 403 whose body extracted to eight words) from ever reaching `ready`. That closes the 403 door, not the 200-status error page this quest is about.

So a plausibility heuristic over the extracted content is still unproven, and the promising direction is a force-restart that re-fetches an item whose stored extraction was wrong, which the retry path deliberately does not do today.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[item-lifecycle]]
