---
title: "Playback speed control"
tags:
  - quest
summary: "Let a listener change playback rate (1x/1.25x/1.5x/2x); straightforward on the audio element, but does highlight sync hold across rates?"
status: open
type: spike
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Playback speed control

## What

Let the listener change playback rate (1×, 1.25×, 1.5×, 2×) on the read-along player. Straightforward on the `<audio>` element itself; the real question is the control's UX and whether [[read-along-timing]]'s highlight sync holds across rates once [[read-along-player]] exists to test it against.

Not yet enumerated as something a single probe could clear.

---

Related: [[quest-log/README|the quest log]] · [[read-along-player]] · [[read-along-timing]]
