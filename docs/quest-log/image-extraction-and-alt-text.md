---
title: "Image extraction and alt text"
tags:
  - adventure
summary: "Carry article images through extraction, render them in the player, and speak their alt text so a listener isn't silently missing content a reader would see."
status: open
kind: journey
priority: 2-soon
created: "2026-07-17"
---

# Image extraction and alt text

## Destination

An article's images survive extraction, render in the player alongside the text, and carry something spoken, so a listener is not silently skipping content a reader would see. Today an image-only unit strips to empty spoken text and is dropped from both lists entirely (see [[article-extraction]]); reaching the end of this means that unit carries something instead of disappearing.

## Bearings

**The ground.** The extraction seam and how the player renders a unit that is not prose. Not TTS voice selection, not the queue, and not the item lifecycle beyond what an image unit needs in order to travel through it.

**Read first.** [[article-extraction]] for how a unit is produced today and why an empty spoken form is dropped; [[what-gets-read-aloud]] for the display and spoken split an image has to fit into; [[read-along-player]] for the focus-mode question this overlaps.

**Standing preferences.** An image is a **non-prose unit**, and the still-open focus-mode question on [[read-along-player]] applies to it: it must not be centre-scaled the way prose is. Alt text is the candidate spoken form rather than a settled one, and how often real articles carry usable alt text is itself unmeasured.

> [!note] The extraction half is built; only the player rendering remains
> The image question was decided and built as part of the extraction-fidelity work, which treated fidelity, images and an AI-generated spoken form as one effort. An article's images now survive extraction, download onto nagara's own storage as WebP keyed by content hash, and carry a spoken form through a precedence: the author's caption verbatim, then a usable alt sentence, then a generated one-sentence description, then a fallback. See [[article-extraction]] and [[the-describer]]. What that work deliberately left out of scope is this adventure's other destination, rendering an image unit in the player, because the player does not exist yet; that overlaps [[read-along-player]] and is the open remainder here.

## Trials

- **How an image unit renders in the player** without being treated as prose, which is the same question focus mode already has open for other non-prose units. This is the open remainder, and it needs the player to exist first.

The first trial this record knew, whether an image unit can carry a spoken form at all, is answered and built (see the callout above).

## Solved

- **An image unit carries a spoken form, and its image survives extraction.** Built by the extraction-fidelity work: images are found by DOM containment, stored as content-hashed WebP, and spoken through the caption / alt / generated-description precedence. The alt-fraction worry it started from is handled by that precedence rather than measured away. What remains is rendering, which waits on the player.

## Out of scope

- **Non-prose units in general.** Code blocks, tables and pull quotes share the shape of this question, but this adventure's destination is images. If an answer generalises that is a gain, not the target.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[read-along-player]] · [[what-gets-read-aloud]]
