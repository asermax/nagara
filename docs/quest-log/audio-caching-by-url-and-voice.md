---
title: "Audio caching by URL and voice"
tags:
  - quest
summary: "Cache generated audio by (url, voice) so two people (or one person re-enqueuing) don't pay to regenerate identical audio."
status: open
kind: build
adventure:
blocked_by: []
priority: 3-later
created: "2026-07-17"
---

# Audio caching by URL and voice

## What

Cache generated audio keyed by `(url, voice)`, so the same article requested again with the same voice reuses the existing audio and timing instead of regenerating it: a compute-cost lever once there is enough volume for it to matter (see [[tts-service]] for the current per-article cost).

Not yet enumerated as something a single slice could clear.

---

Related: [[quest-log/README|the quest log]] · [[tts-service]] · [[persistence-and-storage]]
