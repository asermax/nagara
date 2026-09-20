---
title: "Invariants"
summary: "The ten constraints the code must respect, and where each one is explained."
created: "2026-07-29"
---

# Invariants

## 🔭 Overview

There are ten constraints that the code must respect. Each keeps something true, and the note in each row's last column explains it.

`CLAUDE.md` at the repo root carries the same list for agents working in the codebase. If the two disagree, this note is the explanation and that one is the summary: fix both.

## ⚖️ Rules

| # | Rule | Explained in |
|---|---|---|
| 1 | **One extraction is the source of truth.** The display form and the spoken form both come from one markdown segmentation of the page. The spoken form never reaches a client; the display form is never synthesized. | [article-extraction](article-extraction.md) |
| 2 | **Display, spoken, and timing are properties of one typed unit, never matched by text.** A dropped unit leaves the one list and takes its window with it; a length mismatch at finalize fails the item. | [article-extraction](article-extraction.md), [item-lifecycle](item-lifecycle.md) |
| 3 | **Timing windows are contiguous and the last `end` equals the audio duration.** The inter-paragraph pause is folded into the preceding window, so every instant of playback belongs to exactly one window. | [read-along-timing](read-along-timing.md) |
| 4 | **Every route that touches an item requires the key**: enqueue, poll, and audio alike. `/health` is the only unauthenticated route and carries no item data. | [authentication](authentication.md) |
| 5 | **The API never imports the TTS code.** `tts/` is an image definition uploaded to Modal, not a library; the API spawns it remotely and resolves the call on poll. There is no broker, no worker, and no background sweeper. Deferred work runs inside the API process as a `BackgroundTasks` handler, so it dies with the container; the `queued_at` ceiling and the retry route recover from that. | [tts-service](tts-service.md), [item-lifecycle](item-lifecycle.md) |
| 6 | **Backends are chosen by configuration, never by environment name.** Runtime code has no `if production` and no `if testing`. A half-supplied credential set counts as *not configured*. | [persistence-and-storage](persistence-and-storage.md) |
| 7 | **A schema change is a migration.** Tests build their throwaway schema from the models, so the suite does not exercise the migration path itself: the autogenerate check is what guards it. | [persistence-and-storage](persistence-and-storage.md) |
| 8 | **The three deployables ship independently, and no CI pipeline runs on another's tree.** GitHub Actions path filters and Railway watch paths enforce this. | [deployment-and-ci](deployment-and-ci.md) |
| 9 | **Read-along highlight sync is `requestAnimationFrame`, never `timeupdate`.** The browser's `timeupdate` event fires at only ~4 Hz, too coarse to hold a highlight within a usable tolerance. | [read-along-timing](read-along-timing.md) |
| 10 | **A settled recipe always runs through the deterministic runtime.** The agent that authored or revised a script hands it back as source, and the workflow runs that source like any other recipe to produce the units; a fresh recipe and a years-old one extract through the same deterministic path. | [extraction-service](extraction-service.md) |

> [!NOTE] Invariant 9 applies to `web/`, which does not exist yet
> It is recorded here because the read-along player spike measured it decisively (19–26 ms lag against a 200 ms budget) and it must survive the rewrite; there is no `web/` code today for it to be a property *of* yet.

---

Related: [article-extraction](article-extraction.md) · [item-lifecycle](item-lifecycle.md) · [read-along-timing](read-along-timing.md) · [authentication](authentication.md) · [tts-service](tts-service.md) · [persistence-and-storage](persistence-and-storage.md) · [deployment-and-ci](deployment-and-ci.md) · [extraction-service](extraction-service.md)
