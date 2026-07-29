---
title: "Pin down that markdown adds nothing to the TTS contract"
tags:
  - work
summary: "The requirement that a markdown item's request to and response from the TTS service are identical in shape to a plain-text item's holds by construction, with no branch anywhere enforcing it, and no regression test asserting it."
status: open
kind: chore
priority: whenever
size: small
---

# Pin down that markdown adds nothing to the TTS contract

## What

From the `markdown-read-along-content` spec's R9: "Given the content-generation path, When an item is synthesized, Then the request sent to the TTS service and the shape it returns are the same as for a non-markdown item."

True today by construction: neither `tts/app.py` nor `api/app/service/tts.py` has a markdown-specific branch anywhere, `spawn_synthesis` always takes a plain `list[str]` regardless of what produced it, and `SynthesisResult` is one schema for every item (see [[tts-service]], [[article-extraction]]). Nothing asserts this stays true as a regression guard, though; `chore`, since the behavior is correct today and the risk is a future change quietly adding the branch this note says never to add, not a present bug.

---

Related: [[lab/README|the lab]] · [[tts-service]] · [[article-extraction]]
