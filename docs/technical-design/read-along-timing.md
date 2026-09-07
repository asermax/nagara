---
title: "Read-along timing"
summary: "The pause-fold rule that keeps per-paragraph timing windows contiguous, gapless, and exactly covering the audio."
created: "2026-07-29"
---

# Read-along timing

## 🔭 Overview

Every `ready` item carries a per-paragraph timing window alongside its text (see [item-contract](item-contract.md)), produced by the TTS service ([tts-service](tts-service.md)) and consumed by the read-along player, not yet built in `web/`, and by caption export, which does not exist yet. The pause-fold rule behind those windows applies wherever timing is produced or read.

## 📐 Folding the pause into a window's `end`

`build_timeline` in `tts/app.py` turns each paragraph's rendered duration into a cumulative window, folding the pause into every window but the last:

```python
end = t + dur + (pause_s if i < n - 1 else 0.0)
```

`pause_s` is a fixed 0.1 seconds: long enough to mark a paragraph break without stalling the prose. The exact form of that conditional is the whole rule: every window but the last carries the pause forward into its own `end`.

## 🧩 How a window is built

Each paragraph gets a window `[start, end)`. The next paragraph's `start` equals the previous paragraph's `end`: windows never overlap and never leave a gap. The inter-paragraph silence is folded into the **preceding** paragraph's `end`, and the **last window's `end` equals the total audio duration**.

The resulting timeline is monotonic, non-overlapping, gapless, and covers exactly `[0, duration]`. Every instant of playback belongs to exactly one paragraph.

> [!NOTE] Why the pause is folded into the preceding window
> A read-along consumer maps playback position to a highlighted paragraph by finding the window that contains the current time. Leaving pauses as gaps would drop playback into an un-owned interval during every inter-paragraph silence, flickering the highlight off; folding the pause into the paragraph before it keeps that paragraph highlighted through its trailing pause instead.

> [!NOTE] Why the last end equals the audio duration
> Progress computed as `currentTime / last_end` then reaches 100% exactly as the final paragraph's highlight ends: no drift, no paragraph left highlighted past the audio, no early finish. This holds exactly against real multi-paragraph articles: the last window's `end` matches the measured audio duration to the sample.

## 🎧 What a consumer may assume

- **Highlight**: the active paragraph is the `i` where `start_i <= currentTime < end_i`.
- **Progress**: `currentTime / last_end`, where `last_end` is the audio duration.
- Windows are contiguous and gapless by construction; a consumer must not assume padding between them, and must not add its own.

> [!WARNING] A seek must land just past a unit's start, not exactly on it
> Seeking to paragraph `i`'s exact `start` can round down in a real browser and activate the previous unit instead of `i`. The read-along player spike hit this and fixed it with a small forward nudge past the boundary on every programmatic seek: the player in `web/` must carry the same nudge, since the contract's `start` value alone does not guarantee landing inside the window.

## ⏩ What is not built yet

Word-level timing is out of scope: the contract is paragraph-level only, and the read-along player spike found a per-unit `type` field unnecessary for it (a table-of-contents entry derives from a `#`-prefixed unit instead). Caption export, which does not exist yet, would map these same windows onto cue timings.

---

Related: [item-lifecycle](item-lifecycle.md) · [tts-service](tts-service.md) · [item-contract](item-contract.md) · [article-extraction](article-extraction.md) · [invariants](invariants.md)
