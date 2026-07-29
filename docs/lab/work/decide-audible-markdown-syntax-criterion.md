---
title: "Decide what to do with the audible-markdown-syntax criterion"
tags:
  - work
summary: "Whether the audio reads as natural prose with no vocalized markdown syntax is a human-judgment criterion from the original experiment, and no automated test asserts it."
status: open
kind: chore
priority: whenever
size: small
---

# Decide what to do with the audible-markdown-syntax criterion

## What

From the `markdown-read-along-content` spec's R2: "Given the item's audio, When it is played, Then no markdown syntax is heard and it reads as natural prose."

This is genuinely different from the other three gaps in this batch, which are missing assertions on behavior otherwise known to be correct: this one is a criterion that was judged by a person listening to audio in [[markdown-paragraph-pipeline]] and has no mechanical form. `test_extract.py`'s many strip tests already assert the *mechanical* half (no markdown syntax remains in any `spoken[]` string) extensively and precisely; what they cannot assert is whether the resulting prose sounds natural once Kokoro reads it.

This is a `chore` because there is no known-wrong behavior, but the "resolution" here is a decision rather than a test to write: accept that this criterion stays permanently human-judged and lives only in that experiment's Findings, or find a cheap proxy (a phoneme-count sanity check, a fixed reference recording diffed against a new one) worth the cost of maintaining. Either answer closes this item; only silence does not.

---

Related: [[lab/README|the lab]] · [[markdown-paragraph-pipeline]]
