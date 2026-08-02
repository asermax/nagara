---
title: "Read-along player"
tags:
  - quest
summary: "A web surface where an item's audio and its text are read together: the text following the audio closely enough that listening-while-reading is one activity rather than two."
status: solved
type: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-21"
---

# Read-along player

## What

A web surface where an item's audio and its text are read together: the text following the audio closely enough that listening-while-reading is one activity rather than two. It consumes the existing item contract as-is. Visual design is a different objective, deliberately not this one; see [[read-along-visual-design]].

## Answer

**Promoted: one player, two reading modes.** The decision is recorded; **the real thing is not built.** Graduation to `web/` (TanStack Start + Panda-CSS) is a rewrite: the throwaway spike is preserved on the `idea/read-along-player` branch, with its tree relocated to `web/` rather than carried forward as-is, and its global `ka-*` CSS class names must be scoped or renamed rather than copied verbatim.

De-risked by [[read-along-player-shape]], which cleared:

- The highlight tracks the audio tightly enough to read as read-along: **yes, at 19–26 ms**, but only when driven off `requestAnimationFrame` polling `currentTime`; the `timeupdate` event (~4 Hz) is too coarse. Re-locks immediately after a seek.
- Rendered display markdown and a per-unit highlight coexist: **yes** for headings, emphasis, links, lists and code, end-to-end on two real articles. **Blockquote and table stayed unjudged**: the fixture carried neither and the pre-registered synthetic probe was not built.
- A scroll-decoupled navigation model carries navigation with no click-to-seek: **its mechanics all land** (the follow pill, a heading-derived nested table of contents, ±10 s, resume). Whether it removes the *want* for click-to-seek is builder judgment under the confound, not a fresh-user finding.
- The contract needs no per-unit `type` field or word-level timing: **correct.** The table of contents derives from the `#` prefix; word-level highlighting was dropped.

Still open: how lists, code, and tables behave in focus mode (centring breaks their left-aligned structure); whether the mobile breakpoint holds on a real device (coded, verified only in a desktop harness); whether resume needs a server-side position to follow a listener across devices (faked with localStorage in the spike).

The mechanism facts the rewrite must carry: `requestAnimationFrame`-driven sync (never `timeupdate`); a memoized per-paragraph render so the 60 fps tick does not re-parse markdown; a seek that lands just past a unit's `start` (an exact seek can round down and activate the previous unit); `transform: scale` rather than `font-size` for the enlarged focus-mode line, so it does not reflow surrounding text; a table of contents whose scroll is linked proportionally to the article's own scroll.

Where it lives once built: `technical-design/README.md`'s "What has no note yet" names the gap until then; [[listening-experience|the listening experience]] describes the shape today from this quest's evidence.

How far the evidence reaches: one extended builder-driven session, two real articles, oracle- and builder-confounded: it validates the shape, UX, and functional contract, not demand and not that a fresh user would experience it the same way.

---

Related: [[quest-log/README|the quest log]] · [[read-along-player-shape]] · [[read-along-timing]] · [[item-contract]] · [[listening-experience]] · [[read-along-visual-design]] · [[playback-speed-control]]
