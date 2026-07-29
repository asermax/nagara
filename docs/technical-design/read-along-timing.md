---
title: "Read-along timing"
tags:
  - technical-design
summary: "The pause-fold rule that keeps per-paragraph timing windows contiguous, gapless, and exactly covering the audio."
---

# Read-along timing

Every `ready` item carries a per-paragraph timing window alongside its text (see [[item-contract]]), produced by the TTS service ([[tts-service]]) and consumed by a future read-along player and, eventually, caption export. This note is the pattern behind those windows, load-bearing wherever timing is produced or read.

## Folding the pause into a window's `end`

`build_timeline` in `tts/app.py` turns each paragraph's rendered duration into a cumulative window, folding the pause into every window but the last:

```python
end = t + dur + (pause_s if i < n - 1 else 0.0)
```

`pause_s` is a fixed 0.1 seconds: long enough to mark a paragraph break without stalling the prose. The exact form of that conditional is the whole rule: every window but the last carries the pause forward into its own `end`, which is what the next two sections rely on.

## How a window is built

Each paragraph gets a window `[start, end)`. The next paragraph's `start` equals the previous paragraph's `end`: windows never overlap and never leave a gap. The inter-paragraph silence is folded into the **preceding** paragraph's `end`, not left as an unowned gap between windows, and the **last window's `end` equals the total audio duration**.

The resulting timeline is monotonic, non-overlapping, gapless, and covers exactly `[0, duration]`. Every instant of playback belongs to exactly one paragraph.

> [!note] Why the pause is folded into the preceding window
> A read-along consumer maps playback position to a highlighted paragraph by finding the window that contains the current time. Leaving pauses as gaps would drop playback into an un-owned interval during every inter-paragraph silence, flickering the highlight off; folding the pause into the paragraph before it keeps that paragraph highlighted through its trailing pause instead.

> [!note] Why the last end equals the audio duration
> Progress computed as `currentTime / last_end` then reaches 100% exactly as the final paragraph's highlight ends: no drift, no paragraph left highlighted past the audio, no early finish. This held exactly against real multi-paragraph articles in [[player-ready-item]]: the last window's `end` matched measured audio duration to the sample.

## What a consumer may assume

- **Highlight**: the active paragraph is the `i` where `start_i <= currentTime < end_i`.
- **Progress**: `currentTime / last_end`, where `last_end` is the audio duration.
- Windows are contiguous and gapless by construction; a consumer must not assume padding between them, and must not add its own.

> [!warning] A seek must land just past a unit's start, not exactly on it
> Seeking to paragraph `i`'s exact `start` can round down in a real browser and activate the previous unit instead of `i`. [[read-along-player-shape]] hit this and fixed it with a small forward nudge past the boundary on every programmatic seek: the rewrite in `web/` must carry the same nudge, since the contract's `start` value alone does not guarantee landing inside the window.

## What is not built yet

Word-level timing is out of scope: the contract is paragraph-level only, and a per-unit `type` field was tried against and found unnecessary in [[read-along-player-shape]] (a table-of-contents entry derives from a `#`-prefixed unit instead). Caption export ([[caption-export]]) would map these same windows onto cue timings but does not exist yet.

---

Related: [[item-lifecycle]] · [[tts-service]] · [[item-contract]] · [[article-extraction]] · [[invariants]] · [[read-along-player]]
