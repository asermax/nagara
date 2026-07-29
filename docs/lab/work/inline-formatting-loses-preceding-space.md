---
title: "Inline formatting loses its preceding space"
tags:
  - work
summary: "Links and other inline-formatted runs lose the space separating them from the text before them, corrupting both spoken audio and rendered read-along text."
status: open
kind: defect
priority: next
size: small
---

# Inline formatting loses its preceding space

## What

Links and other inline-formatted runs lose the space that should separate them from the text immediately before them: a source like `click here<a href=…>link</a>` extracts and renders as `click herelink` instead of `click here link`. This corrupts both the spoken audio (the words run together) and the rendered read-along text, in [[article-extraction]]'s display/spoken split.

Observed during real dogfood use through Tachikoma, distinct from the [[markdown-formatted-paragraphs]] faithfulness question: that idea is about whether formatting is captured at all; this is a plain word-boundary bug in extraction or normalization.

---

Related: [[lab/README|the lab]] · [[article-extraction]] · [[markdown-formatted-paragraphs]]
