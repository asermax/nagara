---
title: "Read-along player"
tags:
  - idea
summary: "A web surface where an item's audio and its text are read together: the text following the audio closely enough that listening-while-reading is one activity rather than two."
status: promoted
priority: next
impact: high
size: large
experiments:
  - "[[read-along-player-shape]]"
---

# Read-along player

## Objective

A web surface where an item's audio and its text are read together: the text following the audio closely enough that listening-while-reading is one activity rather than two. It consumes the existing item contract as-is. Visual design is a different objective, deliberately not this one; see [[read-along-visual-design]].

## Unknowns

- ~~Can the highlight track the audio tightly enough in a real browser to read as read-along?~~ → **Yes, at 19–26 ms**, but only when driven off `requestAnimationFrame` polling `currentTime`; the `timeupdate` event (~4 Hz) is too coarse. Re-locks immediately after a seek. [[read-along-player-shape]]
- ~~Can rendered display markdown and a per-unit highlight coexist?~~ → **Yes** for headings, emphasis, links, lists and code, end-to-end on two real articles. **Blockquote and table stayed unjudged**: the fixture carried neither and the pre-registered synthetic probe was not built. [[read-along-player-shape]]
- ~~Can a scroll-decoupled navigation model carry navigation with no click-to-seek?~~ → **Its mechanics all land** (the follow pill, a heading-derived nested table of contents, ±10 s, resume). Whether it removes the *want* for click-to-seek is builder judgment under the confound, not a fresh-user finding. [[read-along-player-shape]]
- ~~Does the contract need a per-unit `type` field or word-level timing?~~ → **No.** The table of contents derives from the `#` prefix; word-level highlighting was dropped. [[read-along-player-shape]]
- Still open: how do lists, code, and tables behave in focus mode? Centring breaks their left-aligned structure: needs per-construct handling.
- Still open: does the mobile breakpoint hold on a real device? Coded, verified only in a desktop harness.
- Still open: does resume need a server-side position so it follows a listener across devices? Faked with localStorage in the spike.

## Conclusion

**Promoted: one player, two reading modes.** The decision is recorded; **the real thing is not built.** Graduation to `web/` (TanStack Start + Panda-CSS) is a rewrite: the throwaway spike is preserved on the `idea/read-along-player` branch, with its tree relocated to `web/` rather than carried forward as-is, and its global `ka-*` CSS class names must be scoped or renamed rather than copied verbatim.

The mechanism facts the rewrite must carry: `requestAnimationFrame`-driven sync (never `timeupdate`); a memoized per-paragraph render so the 60 fps tick does not re-parse markdown; a seek that lands just past a unit's `start` (an exact seek can round down and activate the previous unit); `transform: scale` rather than `font-size` for the enlarged focus-mode line, so it does not reflow surrounding text; a table of contents whose scroll is linked proportionally to the article's own scroll.

Where it lives once built: `technical-design/README.md`'s "What has no note yet" names the gap until then; [[listening-experience|the listening experience]] describes the shape today from this idea's evidence.

How far the evidence reaches: one extended builder-driven session, two real articles, oracle- and builder-confounded: it validates the shape, UX, and functional contract, not demand and not that a fresh user would experience it the same way.

---

Related: [[lab/README|the lab]] · [[read-along-player-shape]] · [[read-along-timing]] · [[item-contract]] · [[listening-experience]] · [[read-along-visual-design]] · [[playback-speed-control]]
