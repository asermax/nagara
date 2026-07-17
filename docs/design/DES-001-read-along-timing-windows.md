# DES-001 — Read-along timing windows (pause-fold rule)

**Status**: Active **Applies to**: the TTS service (timing producer), the item read-along contract, and the future web player (timing consumer) — plus any later caption export **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md)

## Pattern

When producing per-paragraph timing for read-along audio, emit **contiguous, gapless windows** over the audio:

- Each paragraph gets a window `[start, end)`. The next paragraph's `start` equals the previous paragraph's `end` — windows never overlap and never leave a gap.
- The inter-paragraph silence (pause) is **folded into the preceding paragraph's `end`**, not left as an unowned gap between windows.
- The **last window's `end` equals the total audio duration.**

The resulting timeline is monotonic, non-overlapping, gapless, and covers exactly `[0, duration]`. Every instant of playback belongs to exactly one paragraph.

## Rationale

A read-along consumer maps playback position to the highlighted paragraph by finding the window that contains the current time. Two invariants make that reliable:

- **Folding the pause into the preceding window removes dead zones.** If pauses were left as gaps, playback would fall into an un-owned interval during every inter-paragraph silence and the highlight would flicker off. Folding keeps a paragraph highlighted through its trailing pause.
- **`last end == duration` makes the progress bar and the final highlight reconcile exactly.** Progress computed as `time / last_end` reaches 100% precisely as the final paragraph's highlight ends — no drift, no paragraph left highlighted past the audio, no early finish.

These held exactly against real multi-paragraph articles (the last window's `end` matched measured audio duration to the sample).

## How to apply

**Producer** — given each paragraph's rendered duration and a fixed inter-paragraph pause:

```
t = 0
for i, dur in paragraphs:
    end = t + dur + (pause if i is not last else 0)
    window[i] = { start: t, end: end }
    t = end
# t now equals total audio duration (sum of durations + (n-1) pauses)
```

**Consumer** (player / caption export):

- **Highlight**: the active paragraph is the `i` where `start_i <= currentTime < end_i`.
- **Seek**: seeking to paragraph `i` sets playback to `start_i`.
- **Progress**: `currentTime / last_end`, where `last_end` equals the audio duration.

A consumer must not assume padding or gaps between windows; adjacency is guaranteed by the producer.

## Where it is used

- **TTS service** (`tts/`) — produces the timeline with the pause-fold rule and returns it alongside the audio and total duration.
- **Item read-along contract** (`api/` item schema) — carries the per-paragraph `{index, start, end, text}` windows and `duration` through to clients unchanged.
- **Web player** (future read-along surface) — consumes the windows for paragraph highlight, click-to-seek, and the progress bar.
- **Caption export** (future, backlogged) — the same windows map to caption cue timings.
