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

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[item-lifecycle]]
