---
title: "Prose-boilerplate stripping"
tags:
  - idea
summary: "Strip footer, donation, and sponsor-aside paragraphs that arrive as full sentences trafilatura's cruft filter doesn't catch, without over-trimming real content."
status: framed
priority: soon
impact: medium
size: medium
experiments:
---

# Prose-boilerplate stripping

## Objective

Remove prose-boilerplate paragraphs (footer donation asides, sponsor mentions) that trafilatura leaves in as full sentences, seen on the magazine and newsletter fixtures in [[player-ready-item]]. The existing cleanup in [[article-extraction]] only strips safe edge cruft (an echoed title, nav labels, footnote glyphs, punctuation-only units); this is a genuinely harder, heuristic or per-site pass, and the risk to manage is over-trimming real content along with it.

## Unknowns

Not yet enumerated as something a single experiment could clear. This is the accepted-not-cleared residual on [[audio-read-later-queue]]'s promotion.

---

Related: [[lab/README|the lab]] · [[article-extraction]] · [[audio-read-later-queue]]
