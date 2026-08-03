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

> [!info] A live effort outside this vault has already broken much of this ground
> A gitignored working directory in this repository, `.scratch/richer-extraction/`, holds an in-flight mapping of the extraction pipeline whose destination is a locked design written into `docs/`. It treats extraction fidelity, images and an AI-generated spoken form as **one** effort rather than three, on the reasoning that deciding them apart means deciding the image question twice. It is unreachable from a fresh clone and so is not linked as a note, but anyone picking this adventure up should read it first: some of the trials below may already be answered there, and its findings are what should graduate the rest into quests.

## Trials

- **Whether an image unit can carry a spoken form at all.** Alt text is the obvious candidate and may not survive contact with real articles: the question is what fraction carry usable alt text, and what happens to the ones that do not.
- **How an image unit renders in the player** without being treated as prose, which is the same question focus mode already has open for other non-prose units.

Not yet fully enumerated. These two are what this record already knew; the effort named in the bearings is the fastest route to the rest.

## Solved

Nothing yet.

## Out of scope

- **Non-prose units in general.** Code blocks, tables and pull quotes share the shape of this question, but this adventure's destination is images. If an answer generalises that is a gain, not the target.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[read-along-player]] · [[what-gets-read-aloud]]
