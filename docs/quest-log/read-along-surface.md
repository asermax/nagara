---
title: "Read-along surface"
tags:
  - quest
summary: "Build the player in web/: the calm scroll-normal reader, the dark shell, the heading-derived table of contents, and the sync loop, against the item contract unchanged."
status: open
kind: build
adventure: read-along-player
blocked_by: []
priority: 1-now
created: "2026-08-03"
---

# Read-along surface

## What

The first vertical slice of [[read-along-player]]: a real `web/` surface that plays an item's audio and highlights its text in step, end to end on a real generated item. Calm scroll-normal reading mode only. Focus mode, and everything the raid still lists as a trial, comes after.

A slice that leaves the thing working: pick an item, hear it, watch the highlight follow, scroll away and come back, reload and resume.

## Design

`web/` is new, on TanStack Start with Panda-CSS. It consumes `paragraphs[].{index, start, end, display}` plus `duration` and the audio URL, exactly as [[item-contract]] already defines them. No contract change.

Five mechanism facts the spike fixed, each of which the surface breaks without. They are the reason this is a rewrite of the spike rather than a merge of it.

**Sync runs off `requestAnimationFrame` polling `currentTime`, never the `timeupdate` event.** `timeupdate` fires at roughly 4 Hz, far too coarse to hold a highlight. The animation-frame loop held lag to 19–26 ms against a 200 ms budget, and re-locked immediately after a seek. See [[read-along-timing]] and [[invariants]].

**Each paragraph's rendered markdown is memoized.** The loop ticks at 60 fps, and re-parsing markdown every frame reflows the surface and drifts the highlight.

**A programmatic seek lands just past a unit's `start`, not on it.** An exact seek can round down in a real browser and activate the previous unit. A small forward nudge past the boundary fixes it, and the contract's `start` value alone does not guarantee landing inside the window.

**The table of contents derives from `#`-prefixed units** and scrolls proportionally to the article's own scroll rather than item by item, so its position tracks where the reader actually is.

**Focus mode, when it arrives, enlarges the active line with `transform: scale` rather than `font-size`**, because changing font-size reflows the surrounding text. Recorded here because it constrains how the active-line styling is built now, even though focus mode is a later slice.

The spike's global `ka-*` class names are **not** carried over: Panda-CSS scopes styles per component, which is what makes the leak that happened once in the spike impossible here.

Resume uses localStorage keyed by item, matching the spike. Whether it needs a server-side position is a trial on the raid and deliberately not settled here.

---

Related: [[quest-log/README|the quest log]] · [[read-along-player]] · [[read-along-player-shape]] · [[read-along-timing]] · [[item-contract]] · [[listening-experience]]
