---
title: "Decide what to do with the audible-markdown-syntax criterion"
tags:
  - quest
summary: "Whether the audio reads as natural prose with no vocalized markdown syntax is a human-judgment criterion from the original spike, and no automated test asserts it."
status: open
type: design
adventure:
blocked_by: []
priority: 3-later
created: "2026-07-17"
---

# Decide what to do with the audible-markdown-syntax criterion

## What

From the `markdown-read-along-content` spec's R2: "Given the item's audio, When it is played, Then no markdown syntax is heard and it reads as natural prose."

This is genuinely different from the other three gaps in this batch, which are missing assertions on behavior otherwise known to be correct: this one is a criterion that was judged by a person listening to audio in [[markdown-paragraph-pipeline]] and has no mechanical form. `test_extract.py`'s many strip tests already assert the *mechanical* half (no markdown syntax remains in any `spoken[]` string) extensively and precisely; what they cannot assert is whether the resulting prose sounds natural once Kokoro reads it.

This is a decision rather than a test to write: accept that this criterion stays permanently human-judged and lives only in that quest's findings, or find a cheap proxy (a phoneme-count sanity check, a fixed reference recording diffed against a new one) worth the cost of maintaining. Either answer closes this quest; only silence does not.

---

Related: [[quest-log/README|the quest log]] · [[markdown-paragraph-pipeline]]
