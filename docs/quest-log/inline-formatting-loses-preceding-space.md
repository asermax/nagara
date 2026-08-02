---
title: "Inline formatting loses its preceding space"
tags:
  - quest
summary: "Links and other inline-formatted runs lose the space separating them from the text before them, corrupting both spoken audio and rendered read-along text."
status: open
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Inline formatting loses its preceding space

## What

Links and other inline-formatted runs lose the space that should separate them from the text immediately before them: a source like `click here<a href=…>link</a>` extracts and renders as `click herelink` instead of `click here link`. This corrupts both the spoken audio (the words run together) and the rendered read-along text, in [[article-extraction]]'s display/spoken split.

Observed during real dogfood use through Tachikoma, distinct from the [[markdown-formatted-paragraphs]] faithfulness question: that quest is about whether formatting is captured at all; this is a plain word-boundary bug in extraction or normalization.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[markdown-formatted-paragraphs]]
