---
title: "Read-along player"
tags:
  - adventure
summary: "Build the read-along surface in web/: one player, two reading modes, on the existing item contract, with the shape already settled by a spike."
status: open
kind: raid
priority: 1-now
created: "2026-07-21"
---

# Read-along player

## Destination

A web surface at `web/` where an item's audio and its text are read together, the text following the audio closely enough that listening-while-reading is one activity rather than two. One player with two reading modes: calm scroll-normal by default, an opt-in focus mode that centres and enlarges the active paragraph. It consumes the existing item contract unchanged.

Reaching the end means the surface is built, deployed, and dogfooded on real generated items, and its mechanism lives in `docs/technical-design/` as a durable note.

No journey preceded this. The ground was cleared by a single spike, [[read-along-player-shape]], and the reasoning behind every shape decision lives there rather than here.

## Bearings

**The ground.** `web/`, which does not exist on `main` yet. The item contract is fixed and this adventure does not change it: no per-unit `type` field, no word-level timing. Nothing in `api/` or `tts/`.

**Read first.** [[listening-experience]] for the shape as it stands, [[read-along-timing]] for the timing mechanism and the seek nudge, [[item-contract]] for what the player consumes, [[invariants]] for the sync budget. `CLAUDE.md` says what a new surface obliges you to write.

**Standing preferences.**

The stack is TanStack Start with Panda-CSS, and graduation is **a rewrite rather than a merge**. The spike is preserved on the unmerged `idea/read-along-player` branch with its tree relocated to `web/` so it sits where the real surface gets built. Read it; do not carry it forward as-is.

Two things from the spike must not be copied verbatim. Its global `ka-*` CSS class names leaked between components once already and have to be scoped or renamed. Its localStorage resume is a stand-in rather than a decision.

Visual design is **not** this adventure's, and the placeholder aesthetic the spike used carries no verdict weight. [[read-along-visual-design]] owns typography, colour, motion and brand feel, and it treats this player's layout and navigation as the fixed substrate it must not disturb.

> [!warning] The shape evidence is builder-confounded by construction
> The same person built the spike and judged it, across one extended session on two real articles. It validates shape, UX and the functional contract. It is not evidence of demand, and not evidence that a fresh user would experience it the same way. Anything that needs a fresh user belongs to [[validate-demand]].

## Trials

Three of these mean the ground was not fully clear when this raid started. They are recorded rather than smoothed over, and each blocks a slice rather than the whole build.

**How lists, code and tables behave in focus mode.** Centring and enlarging the active line breaks their left-aligned structure, and the spike never settled what should happen instead.

**Whether blockquote and table render and highlight correctly.** The spike's pre-registered synthetic probe for these two was never built, so they are genuinely unjudged rather than passed. Every other construct held on two real articles.

**Whether the mobile breakpoint holds on a real device.** Coded in the spike, verified only in a desktop harness.

**Whether resume needs a server-side position** to follow a listener across devices, rather than the per-browser localStorage the spike faked it with.

## Solved

- [[read-along-player-shape]] — settled the whole shape: one player with two reading modes, a dark immersive shell, a heading-derived floating table of contents, and a scroll-decoupled navigation model with no click-to-seek. Fixed the sync mechanism at 19–26 ms off `requestAnimationFrame`, and confirmed the contract needs no `type` field and no word-level timing. Left a working spike on the unmerged `idea/read-along-player` branch, tree at `web/`.

## Out of scope

**Visual design.** [[read-along-visual-design]] owns it, against this player's layout as a fixed substrate.

**Click-to-seek.** Deliberately absent, replaced by the scroll-decoupled follow pill. Whether its absence is felt as friction by anyone other than the builder is a demand question rather than this one.

**Word-level highlighting.** Dropped: the contract is paragraph-level and the spike found nothing that needed finer.

**Caption export.** [[caption-export]] maps the same timing windows onto cue timings and is its own thing.

---

Related: [[quest-log/README|the quest log]] · [[read-along-player-shape]] · [[read-along-timing]] · [[item-contract]] · [[listening-experience]] · [[read-along-visual-design]]
