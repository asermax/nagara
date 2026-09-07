---
title: "Listening experience"
summary: "Read-along as the product: a calm reader by default, an opt-in focus teleprompter, and navigation carried entirely by scroll and a table of contents rather than clicking into the text."
created: "2026-07-29"
---

# Listening experience

## 🔭 Overview

Read-along is the point of nagara: the text follows the audio closely enough that listening and reading are one activity. The shape described here is settled against real generated items; the player itself is not yet built in `web/`.

## 📖 One player, two reading modes

The default is a **calm, scroll-normal reader**: full-brightness text, a single background-fill highlight on the paragraph currently playing, nothing dimmed. An opt-in **focus mode** switches to a teleprompter treatment instead: the active paragraph is pinned to the centre of the view and enlarged, with past and upcoming text dimmed around it, for a listener who wants to lock onto exactly the words being spoken. Both modes share one dark, immersive shell: a floating table of contents, a floating transport, and a progress bar.

> [!NOTE] Why the shape is two modes of one player, not a choice between two designs
> A calm scroll-normal reader and an aggressive teleprompter look like competing archetypes. Every iteration on the teleprompter removes one of its own signature moves (dimming, fade gradients, the centre-pin) while the immersive shell around it stays. The two are not competing for the same listener; they are two moments the same listener wants at different times, so they are a toggle on one player instead of a decision between two.

## 🧭 Navigation with no click-to-seek

There is no click-into-the-text seek. Instead: a scroll "follow from here" affordance re-anchors playback to wherever the reader has scrolled to; a floating table of contents, derived from the article's own headings, jumps to a section; a ±10 second skip moves by a fixed amount. Scrolling away from the currently-playing paragraph does not pause or otherwise fight the reader: the two are decoupled, and following resumes on its own after the playing position has been back in view for a short dwell.

> [!WARNING] A seek must land just past a paragraph's start, not exactly on it
> Landing exactly on a boundary can round down in a real browser and activate the previous paragraph instead. See [read-along-timing](../technical-design/read-along-timing.md)'s warning on this: every programmatic seek nudges forward past the boundary to avoid it.

## ⏯️ Resume

Reloading the page restores playback to the position last reached. That position lives in the browser's local storage, keyed by item; it does not follow a listener across devices.

## ⏩ What is not built yet

A link back to the source article, and a share action that shares that original URL rather than the player link.

---

Related: [read-along-timing](../technical-design/read-along-timing.md) · [item-contract](../technical-design/item-contract.md) · [what-gets-read-aloud](what-gets-read-aloud.md)
