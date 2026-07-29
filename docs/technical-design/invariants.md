---
title: "Invariants"
tags:
  - technical-design
summary: "The nine rules the code obeys, and where each one is explained."
---

# Invariants

Nine rules the code actually obeys. They are constraints rather than aspirations: each is load-bearing for something, and the note in the last column is where that something is explained.

`CLAUDE.md` at the repo root carries the same list for agents working in the codebase. If the two disagree, this note is the explanation and that one is the summary: fix both.

| # | Rule | Explained in |
|---|---|---|
| 1 | **One extraction is the source of truth.** The spoken form never reaches a client and the display form is never synthesized: both are derived from one markdown segmentation. | [[article-extraction]] |
| 2 | **`display[i]`, `spoken[i]`, and `timeline[i]` are the same unit by construction, never by matching text.** A unit dropped for any reason is dropped from *both* lists; a length mismatch at finalize fails the item rather than mis-mapping formatting onto the wrong window. | [[article-extraction]], [[item-lifecycle]] |
| 3 | **Timing windows are contiguous and the last `end` equals the audio duration.** The inter-paragraph pause is folded into the preceding window; there is no un-owned interval and no dead highlight zone. | [[read-along-timing]] |
| 4 | **Every route that touches an item requires the key**: enqueue, poll, and audio alike. `/health` is the only unauthenticated route and carries no item data. | [[authentication]] |
| 5 | **The API never imports the TTS code.** `tts/` is an image definition uploaded to Modal, not a library; the API spawns and resolves it remotely: no broker, no worker, no background sweeper. | [[tts-service]], [[item-lifecycle]] |
| 6 | **Which backend is a question about configuration, never an environment name.** No `if production`, no `if testing` in runtime code; a half-supplied credential set counts as *not configured*. | [[persistence-and-storage]] |
| 7 | **A schema change is a migration.** Tests build their throwaway schema from the models, so the migration path itself is not exercised by the suite: the autogenerate check is what guards it. | [[persistence-and-storage]] |
| 8 | **The two deployables ship independently, and neither pipeline reaches into the other's tree.** Path filters on both GitHub Actions and Railway watch paths are the mechanism. | [[deployment-and-ci]] |
| 9 | **Read-along highlight sync is `requestAnimationFrame`, never `timeupdate`.** The browser's `timeupdate` event fires at only ~4 Hz, too coarse to hold a highlight within a usable tolerance. | [[read-along-timing]], [[read-along-player]] |

> [!note] Invariant 9 applies to `web/`, which does not exist yet
> It is recorded here because [[read-along-player-shape]] measured it decisively (19–26 ms lag against a 200 ms budget) and it must survive the rewrite; there is no `web/` code today for it to be a property *of* yet.

---

Related: [[article-extraction]] · [[item-lifecycle]] · [[read-along-timing]] · [[authentication]] · [[tts-service]] · [[persistence-and-storage]] · [[deployment-and-ci]] · [[read-along-player]]
