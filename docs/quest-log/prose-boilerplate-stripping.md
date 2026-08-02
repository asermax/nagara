---
title: "Prose-boilerplate stripping"
tags:
  - quest
summary: "Strip footer, donation, and sponsor-aside paragraphs that arrive as full sentences trafilatura's cruft filter doesn't catch, without over-trimming real content."
status: open
type: spike
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Prose-boilerplate stripping

## What

Remove prose-boilerplate paragraphs (footer donation asides, sponsor mentions) that trafilatura leaves in as full sentences, seen on the magazine and newsletter fixtures in [[player-ready-item]]. The existing cleanup in [[article-extraction]] only strips safe edge cruft (an echoed title, nav labels, footnote glyphs, punctuation-only units); this is a genuinely harder, heuristic or per-site pass, and the risk to manage is over-trimming real content along with it.

Not yet enumerated as something a single probe could clear. This is the accepted-not-cleared residual on [[audio-read-later-queue]]'s promotion.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[audio-read-later-queue]]
