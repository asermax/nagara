---
title: "Product design"
summary: "Index of the notes about what nagara is and what it is like to use"
---

# Product design

This folder holds what nagara is and what it is like to use. Each note explains one part of it; the reasoning behind a choice sits in a callout next to the mechanism it justifies. See [the docs charter](../README.md) for how a note is written.

## What notes exist

One row per note, kept by hand: adding a note here is part of writing it.

| Note | Explains |
|---|---|
| [what-nagara-is](what-nagara-is.md) | A private, API-first audio read-later queue (hand it a URL, get back listenable read-along audio) built to answer one open question: does anyone besides the owner want this? |
| [queue](queue.md) | Every item is private to the key that created it; a voice is chosen per item or at random from a curated pool, and a status a user can see maps directly onto generating, ready, or failed. |
| [listening-experience](listening-experience.md) | Read-along as the product: a calm reader by default, an opt-in focus teleprompter, and navigation carried entirely by scroll and a table of contents rather than clicking into the text. |
| [what-gets-read-aloud](what-gets-read-aloud.md) | The article body, and nothing else: a code block and an image are each described in one spoken sentence, a table reads as prose, a link reads as its anchor text, and the author's own words are preferred wherever they exist. |

## What has no note yet

Honest gaps, so nobody assumes coverage that is not there.

- **The read-along player's visual design.** [The listening experience](listening-experience.md) describes the player's shape (two reading modes, scroll-decoupled navigation), settled against a deliberately placeholder aesthetic. The design language (typography, colour, motion, brand feel) is unbuilt; it is the Read-along visual design milestone in Linear.
