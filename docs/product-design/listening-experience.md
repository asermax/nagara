---
title: "Listening experience"
tags:
  - product-design
summary: "Read-along as the product: a calm reader by default, an opt-in focus teleprompter, and navigation carried entirely by scroll and a table of contents rather than clicking into the text."
---

# Listening experience

Read-along is the point of nagara, not a feature bolted onto plain audio playback: the text follows the audio closely enough that listening and reading are one activity. [[read-along-player-shape]] settled this shape against real generated items; [[read-along-player]] carries the decision to build it for real, not yet done.

## One player, two reading modes

The default is a **calm, scroll-normal reader**: full-brightness text, a single background-fill highlight on the paragraph currently playing, nothing dimmed. An opt-in **focus mode** switches to a teleprompter treatment instead: the active paragraph is pinned to the centre of the view and enlarged, with past and upcoming text dimmed around it, for a listener who wants to lock onto exactly the words being spoken. Both modes share one dark, immersive shell: a floating table of contents, a floating transport, and a progress bar.

> [!note] Why the shape converged into modes of one player, not a choice between two designs
> Early mockups treated a calm scroll-normal reader and an aggressive teleprompter as competing archetypes. Iterating on the teleprompter kept removing its own signature moves (dimming, fade gradients, the centre-pin) while the immersive shell around it stayed. The two were not actually competing for the same listener; they were two moments the same listener wants at different times, so they became a toggle on one player instead of a decision between two.

## Navigation with no click-to-seek

There is no click-into-the-text seek. Instead: a scroll "follow from here" affordance re-anchors playback to wherever the reader has scrolled to; a floating table of contents, derived from the article's own headings, jumps to a section; a ±10 second skip moves by a fixed amount. Scrolling away from the currently-playing paragraph does not pause or otherwise fight the reader: the two are decoupled, and following resumes on its own after the playing position has been back in view for a short dwell.

> [!warning] A seek must land just past a paragraph's start, not exactly on it
> Landing exactly on a boundary can round down in a real browser and activate the previous paragraph instead. See [[read-along-timing]]'s warning on this: every programmatic seek nudges forward past the boundary to avoid it.

## Resume

Reloading the page restores playback to the position last reached. Today that position lives in the browser's local storage, keyed by item; it does not yet follow a listener across devices, see [[read-along-player]]'s open unknowns.

## What is not built yet

A link back to the source article, and a share action that shares that original URL rather than the player link; see [[link-to-original-and-share]].

---

Related: [[read-along-player]] · [[read-along-timing]] · [[item-contract]] · [[read-along-visual-design]] · [[what-gets-read-aloud]] · [[link-to-original-and-share]]
