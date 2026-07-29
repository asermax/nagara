---
title: "Trustworthy extraction"
tags:
  - idea
summary: "Be able to trust that a ready item is actually the article it claims to be, not a 200-status error page read aloud."
status: shaped
priority: next
impact: high
size: medium
experiments:
---

# Trustworthy extraction

## Objective

Be able to trust that a `ready` item is the article it claims to be. Today a URL serving an HTTP `200` error page (a GitHub Pages 404, say) extracts successfully, so the pipeline generates audio of the error page being read aloud: the worst failure mode this project has, because it looks exactly like a working item and the status is never `failed` (see [[item-lifecycle]]'s warning on this). Nothing in [[article-extraction]] catches it.

## Unknowns

- Does a heuristic that checks the extracted paragraphs for real content (title presence, length, known error-page shapes) separate an error page from a short but legitimate article, without rejecting real content along the way? Not yet tried. This is the whole difficulty: a naive length or title check risks throwing out a real short article exactly as readily as it catches a fake one, and nobody has looked at what real error pages and real short articles actually look like side by side.

---

Related: [[lab/README|the lab]] · [[article-extraction]] · [[item-lifecycle]]
