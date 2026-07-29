---
title: "Audio caching by URL and voice"
tags:
  - idea
summary: "Cache generated audio by (url, voice) so two people (or one person re-enqueuing) don't pay to regenerate identical audio."
status: raw
priority: whenever
impact: low
size: small
experiments:
---

# Audio caching by URL and voice

## Objective

Cache generated audio keyed by `(url, voice)`, so the same article requested again with the same voice reuses the existing audio and timing instead of regenerating it: a compute-cost lever once there is enough volume for it to matter (see [[tts-service]] for the current per-article cost).

## Unknowns

Not yet enumerated as something a single experiment could clear.

---

Related: [[lab/README|the lab]] · [[tts-service]] · [[persistence-and-storage]]
