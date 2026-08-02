---
title: "Read-along player shape"
tags:
  - quest
summary: "What player shape makes read-along actually work? One player, two modes: a calm scroll-normal reader by default and an opt-in focus teleprompter, inside a dark shell with a scroll-decoupled navigation model; blockquote and table render/highlight stayed unjudged."
status: solved
type: spike
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-21"
---

# Read-along player shape

## What

Serves [[read-along-player]], a web surface where an item's audio and text are read together closely enough that listening-while-reading is one activity. Ran as an isolated, throwaway Vite+React spike, built on `main` at `experiments/003-read-along-player/spike/` (a deliberate deviation from graduate-in-place, later adopted as the project's convention; see [[quest-log/README|the quest log's]] "How we work"). The spike now lives on the `idea/read-along-player` branch instead, its tree relocated to `web/` so it sits where the real surface gets built. `main` carries no `web/` tree, because a Vite app that is not production code has no business in the tree `main` describes.

`partial` rather than `cleared`: task 2 (markdown render + highlight) passed for every construct the real fixtures carried, but the pre-registered synthetic probe for blockquote and table was never built, so disproof condition 2 is unjudgeable (not passed) for those two constructs.

This is discovery-mode: the *judgment* was fixed in advance; the *shape* is what the spike discovered, by building several coherent whole-screen mockups and recombining them rather than committing to one design up front (see [[quest-log/README|the quest log's]] "explore several variants and recombine" method note).

The unknowns it clears:

- Can the highlight track the audio tightly enough in a real browser to read as read-along?
- Can rendered display markdown and a per-unit highlight coexist?
- Can a scroll-decoupled navigation model (a seek-to-here follow pill, a floating table of contents, ±10 s skip, and resume) carry navigation with no click-to-seek?
- Does the item contract need a per-unit `type` field or word-level timing?

## Design

A simple React player consuming `paragraphs[].{index, start, end, display}` + `duration` + audio, judged against the real M1/M2 item contract on real generated items, not mock content. Click-to-seek is deliberately absent, replaced by the scroll-decoupled model; the test is whether its absence creates friction, not a head-to-head against it.

Method: breadth-then-depth. Phase 1 built four static whole-screen mockups on real article content, hardcoded to one active unit, no audio: an Immersive Reader (centred column, dimming-as-highlight), a Podcast-app (bottom player bar, background-fill highlight, left ToC rail), a Document+rail (right rail, left-accent highlight), and a Karaoke/teleprompter (centre-pinned enlarged active line, auto-scroll). Phase 2 wired the chosen shape to a shared functional core: highlight sync off `requestAnimationFrame` polling `currentTime` against each unit's `[start, end)` window (the browser's `timeupdate` event fires only ~4 Hz, too coarse), markdown render with a client-derived table of contents from heading units, the scroll-decoupled navigation model, and localStorage resume.

Real data: the Mitchell Hashimoto fixture (55 units, ~14 min, from [[markdown-paragraph-pipeline]]) for sync, transport and markdown emphasis; a second, richer real item generated for this experiment (Martin Fowler's "Micro Frontends", 172 units, 31 headings, 19 code blocks, ~40 min) for a genuine multi-entry table of contents and code rendering; a hand-crafted synthetic item (blockquote, fenced code block, table, plausible fixed timing, hardcoded clock) intended to cover blockquote and table render/highlight at the render level only.

### Acceptance criteria

Pre-registered 2026-07-21 before any of it was built; the numbered conditions below are the original disproof list, unedited. Disproven if any of:

1. **Highlight can't track**: the active paragraph drifts or jitters against `currentTime` badly enough to break the read-along feel, or fails to re-lock immediately after a seek;
2. **Markdown and highlight can't coexist**: rendered display markdown cannot be highlighted cleanly per-unit, or the highlight mangles the rendered formatting;
3. **The navigation model fails**: seek-to-here lands on the wrong audio position, the follow pill fights the reader, the table of contents targets the wrong unit, or ±10 s skip desyncs highlight from audio;
4. **The shape doesn't cohere**: resume restores the wrong unit; a built affordance goes unused across a full-article read; or the scroll-decoupled model creates enough friction that the builder finds themself reaching for a click-to-seek that isn't there.

Task criteria: playing a real item start to finish keeps the highlighted unit in sync within 200 ms of each boundary, including immediately after a seek; markdown renders and highlights correctly, including the synthetic probe's blockquote/code/table; seek-to-here, ±10 s, and a ToC entry each land on the correct audio position; reloading the page restores playback position to the correct unit.

The synthetic probe covers blockquote/code/table at the **render level only**: no real item carrying them has been generated end-to-end, and that gap is not a gate on this experiment.

## Answer

### 2026-07-21: the shell wanted is dark and immersive, the reading surface wanted is calm, not a teleprompter

All four archetypes were built and reviewed side by side on real content. The Karaoke archetype's visuals drew the first clear positive reaction, but iterating on it converged toward removing its own signature moves, the dimming, the fade gradients, the centre-pin, while keeping its dark immersive shell and floating table of contents. A requested hybrid (Karaoke's shell with the Podcast-app's calm scroll-normal reading body) became the pulling favourite. The insight: the "wow" was quiet legibility inside an immersive frame, with the highlight as the only motion. The aggressive teleprompter treatment was over-designed for sustained reading.

### 2026-07-21: the shape converged into modes of one player, not a choice between two

Rather than pick one archetype over the other, the calm reader and the teleprompter became a `focus` toggle on a single player: calm scroll-normal by default, an opt-in centred-and-enlarged focus mode for locking onto the current paragraph, sharing one dark immersive shell (floating table of contents, floating transport, progress bar).

### 2026-07-21: visual design was explicitly out of scope

The mockups answer *shape*, layout, navigation, usability, the mode structure, not visual design. The placeholder aesthetic (palette, type scale, spacing) carries no verdict weight; proper visual design is a separate, later quest (see [[read-along-visual-design]]).

### 2026-07-21: sync held comfortably at 19 to 26 ms, re-locking immediately after a seek

`requestAnimationFrame` polling `currentTime` (not `timeupdate`) held highlight lag at two measured boundaries to 19 ms and 26 ms, roughly one to two frames, far inside the 200 ms criterion, and re-locked immediately after both a skip and a progress-bar seek. Per-paragraph memoization kept the 60 fps tick from re-parsing markdown on every frame.

### 2026-07-21: navigation landed correctly, and resume restored exactly

±10 s skip moved audio and the highlight followed; the scroll follow-pill appeared on manual scroll and, clicked, jumped audio to the reading position, resumed, and re-engaged auto-follow; a full reload restored the exact playback position from localStorage. The table of contents was still wired to a placeholder list at this point; the real heading-derived version needed the richer fixture, generated next.

### 2026-07-21: the richer fixture closed markdown+highlight coexistence for headings, lists, and code, but not blockquote or table

Generating a real, formatting-dense item (31 headings, 19 code blocks, 20 list items) gave a genuine nested, multi-entry table of contents derived from real headings, with code blocks rendering with syntax highlighting and sync holding on a 40-minute file. The chosen article carried no blockquote and no table, and, recorded here rather than smoothed over, **the pre-registered synthetic probe for those two constructs was never built.** Disproof condition 2 is therefore exercised and passed for headings, emphasis, links, lists, and code, and genuinely unjudged, not passed, for blockquote and table.

### 2026-07-21: a seek can round down below a unit's boundary

Seeking to a unit's exact `start` occasionally landed just before it, activating the previous unit instead. Fixed with a small forward nudge past the boundary on every programmatic seek.

### 2026-07-21: the spike's global CSS class names leaked between components

The wired player reused the static mockups' shared class names, and one archetype's global rule leaked into the shared table-of-contents styling, pulling it out of its wrapper. Fixed locally, but flagged as a graduation risk: the real `web/` build must scope or rename these class names rather than carry the spike's global CSS forward verbatim.

**Partial.** No disproof condition triggered where it could be exercised, and the shape cohered: one player with two reading modes, a calm scroll-normal default and an opt-in focus teleprompter, inside a dark immersive shell with a floating heading-derived table of contents (nested, article-linked proportional scroll, edge fades, jump arrows), a floating transport, a scroll-decoupled seek-to-here follow pill, ±10 s skip, and localStorage resume, consuming the M1/M2 item contract unchanged. Task 1 (sync) passed comfortably; task 3 (navigation) passed; task 4 (resume) passed; task 2 (markdown render + highlight) passed for headings, emphasis, links, lists, and code on two real articles, and is **unjudged**, not passed, for blockquote and table, because the pre-registered synthetic probe for them was never built. The felt judgment that the scroll-decoupled model fully removed the want for click-to-seek is the builder's impression under the confound below, not a logged fresh-user reflection.

**Scope.** Self-use, one extended builder-driven session, two real articles (a clean ~14-minute piece and a rich ~40-minute, 31-heading, 19-code-block piece), a throwaway Vite+React spike. Oracle- and builder-confounded by construction: the same person built the player and judged it. So this validates the *shape, UX, and functional contract*, not demand and not that a fresh user would experience it the same way. Visual design was explicitly excluded.

---

Related: [[quest-log/README|the quest log]] · [[read-along-player]] · [[read-along-timing]] · [[item-contract]] · [[markdown-paragraph-pipeline]]
