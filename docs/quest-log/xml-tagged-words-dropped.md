---
title: "XML-tagged words dropped"
tags:
  - quest
summary: "Audio silently drops words wrapped in XML-like tags; strip or escape them before they reach the TTS."
status: open
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# XML-tagged words dropped

## What

Audio silently drops words wrapped in XML-like tags (e.g. `<software>`). The TTS engine appears to strip tagged tokens instead of reading the word content. Needs investigation — either strip tags before sending to TTS, or escape them properly.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[what-gets-read-aloud]]
