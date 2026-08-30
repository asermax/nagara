---
title: "Missing quotes and code blocks"
tags:
  - quest
summary: "Quoted text and code blocks are missing from some listen articles; find out whether it is fetch-side or parse-side."
status: open
kind: spike
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# Missing quotes and code blocks

## What

Quoted text and code blocks are missing from some listen articles, e.g. Armin's "What is Reasoning?". Need to check if it's a fetch issue (nagara not extracting) or parse-side (our build dropping them). Data point: the extensible-software nagara response DID include `code` type units (13), so code extraction works there — suspicion: fetch-side issue or markdown blockquote handling.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[what-gets-read-aloud]]
