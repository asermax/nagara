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
| 5 | **No Worker imports the TTS code.** `tts/` is an image definition uploaded to Modal, not a library; the item Workflow reaches it over HTTP through two web endpoints behind Modal's proxy auth, starting a synthesis and polling for its result. There is no broker and no background sweeper. Deferred work runs as the item Workflow's steps, each retried on its own; the retry route restarts a failed item from the step that failed, and the API queues an item again when it reads one that has been queued for more than 15 minutes. | [tts-service](tts-service.md), [item-lifecycle](item-lifecycle.md) |
| 6 | **Backends are chosen by configuration, never by environment name.** Runtime code has no `if production` and no `if testing`. | [persistence-and-storage](persistence-and-storage.md) |
| 7 | **A schema change is a migration.** The D1 schema is `common/src/db/schema.ts`, the one source both the queries' types and the migrations come from. drizzle-kit generates each SQL migration from it, and the developer reviews and commits the SQL like code; CI fails a change whose schema has no matching migration. The Cloudflare CI workflow's migrate job applies the migrations with wrangler before either Worker deploys. The Workers' tests build their D1 schema by applying the same migrations, so the suite exercises the migration path itself. | [persistence-and-storage](persistence-and-storage.md), [common-package](common-package.md) |
| 8 | **The three deployables ship separately, and no CI pipeline runs on another's tree except `common/`'s.** GitHub Actions path filters enforce this. A change to `common/` runs the type checks of both Workers, and one Cloudflare workflow deploys in a fixed order: `common/`'s migrations, then the pipeline Worker, then the API Worker. | [deployment-and-ci](deployment-and-ci.md) |
| 9 | **Read-along highlight sync is `requestAnimationFrame`, never `timeupdate`.** The browser's `timeupdate` event fires at only ~4 Hz, too coarse to hold a highlight within a usable tolerance. | [read-along-timing](read-along-timing.md) |
| 10 | **A settled recipe always runs through the deterministic runtime.** The agent that authored or revised a script hands it back as source, and the item Workflow's recipe step runs that source like any other recipe to produce the units; a fresh recipe and a years-old one extract through the same deterministic path. | [item-lifecycle](item-lifecycle.md), [recipes](recipes.md) |

> [!NOTE] Invariant 9 applies to `web/`, which does not exist yet
> It is recorded here because the read-along player spike measured it decisively (19–26 ms lag against a 200 ms budget) and it must survive the rewrite; there is no `web/` code today for it to be a property *of* yet.

---

Related: [article-extraction](article-extraction.md) · [item-lifecycle](item-lifecycle.md) · [read-along-timing](read-along-timing.md) · [authentication](authentication.md) · [tts-service](tts-service.md) · [persistence-and-storage](persistence-and-storage.md) · [common-package](common-package.md) · [deployment-and-ci](deployment-and-ci.md) · [recipes](recipes.md)
