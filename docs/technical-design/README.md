---
title: "Technical design"
tags:
  - technical-design
  - index
summary: "Index and reading order for the notes about how the code works."
---

# Technical design

How the code works. Each note explains one part of the system; the reasoning behind a choice sits in a callout next to the mechanism it justifies. See [[the vault index]] for the writing charter.

## Reading order

If you are new, read these three in order, because they are the spine and everything else assumes them:

1. [[item-lifecycle]]: the four-state machine, a mortal in-process task that enriches and spawns, lazy resolve on poll
2. [[article-extraction]]: how a URL becomes the display and spoken paragraph lists
3. [[read-along-timing]]: how those paragraphs get contiguous timing windows

Then whatever you are touching.

## What notes exist

Every note tagged `technical-design`, with its own summary. The list is generated, so a new note appears here by existing: there is no row to remember to add.

![[technical-design-notes.base]]

## What has no note yet

Honest gaps, so nobody assumes coverage that is not there:

- **The read-along player.** [[read-along-player]] is a promoted idea, not yet built in `web/`: a note explains how a part *works*, and there is no part yet. Its mechanism facts (`requestAnimationFrame`-driven highlight sync, the seek nudge past a unit's start, memoized per-paragraph render, `transform: scale` for focus mode, the ToC's proportional scroll) live in that idea's `## Conclusion` and in [[read-along-player-shape]] until graduation, at which point this gap gets its note.
