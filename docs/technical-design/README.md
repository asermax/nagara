---
title: "Technical design"
summary: "Index of the notes about how the code works"
---

# Technical design

This folder holds how the code works. Each note explains one part of it; the reasoning behind a choice sits in a callout next to the mechanism it justifies. See [the docs charter](../README.md) for how a note is written.

## Reading order

Read these three in order since everything else depends on them:

1. [item-lifecycle](item-lifecycle.md): the four-state machine, a mortal in-process task that fetches and spawns extraction, lazy resolve on poll
2. [article-extraction](article-extraction.md): how a fetched article becomes the item's typed units, each carrying its display and spoken form
3. [read-along-timing](read-along-timing.md): how those paragraphs get contiguous timing windows

Then whatever you are touching.

## What notes exist

One row per note, kept by hand: adding a note here is part of writing it.

| Note | Explains |
|---|---|
| [item-lifecycle](item-lifecycle.md) | The item's four-state machine: enqueue commits a queued row, a mortal in-process task fetches the article and spawns its extraction job, poll resolves extraction, enrichment and synthesis to ready or failed, and retry re-drives from the phase that failed. |
| [article-extraction](article-extraction.md) | How the API fetches an article and turns the extraction service's markdown units into the item's typed units: a spoken form derived from each unit's display, a drop for a unit with nothing to say, and the acquisition of the article's declared images. |
| [recipes](recipes.md) | How one agent-authored script per domain extracts the domain's articles into markdown units, its versioned record, how a URL matches to it, and how agents author and revise it. |
| [markdown-units](markdown-units.md) | What a unit's display markdown carries for each source element, and how the shared converter, the validator and the title unit turn a recipe's declared elements into it. |
| [extraction-service](extraction-service.md) | The extraction pipeline as a service on Cloudflare: a Worker entrypoint, a per-domain queue Durable Object, one Workflow per job, and Flue agents, called by the API with spawn-and-resolve. |
| [read-along-timing](read-along-timing.md) | The pause-fold rule that keeps per-paragraph timing windows contiguous, gapless, and exactly covering the audio. |
| [the-describer](the-describer.md) | The Gemini describer: one generated sentence for a block a listener can't see, reused by the code path and the image path, floored and capped against one shared per-item budget. |
| [tts-service](tts-service.md) | Kokoro-82M on Modal, a separate deployable the API invokes remotely with no broker: spawn, persist the handle, resolve lazily on poll. |
| [item-contract](item-contract.md) | The item routes plus /health, the item JSON, and the typed display unit whose spoken form is projected out at the response boundary. |
| [persistence-and-storage](persistence-and-storage.md) | The item as an ORM row with JSON `units` and `degradations` columns, migrated by Alembic; audio and images in separate stores with a cost ledger beside them, every backend selected from configuration, never an environment name. |
| [authentication](authentication.md) | A single API key is the user's identity and guards every item route; audio reaches a headerless browser through a short-lived link minted only to an authenticated caller. |
| [deployment-and-ci](deployment-and-ci.md) | Three independent deployables (Railway serverless for the API, Modal for the TTS service, Cloudflare for the extraction service), each with its own path-filtered CI pipeline; none reaches into another's tree. |
| [invariants](invariants.md) | The nine rules the code obeys, and where each one is explained. |

## What has no note yet

Honest gaps, so nobody assumes coverage that is not there.

- **The read-along player.** Not yet built in `web/`, so there is no part to explain. Its mechanism facts are settled: the `requestAnimationFrame` highlight sync and the seek nudge in [read-along-timing](read-along-timing.md), the shape of the surface in [the listening experience](../product-design/listening-experience.md), and the rest (memoized per-paragraph render, `transform: scale` for focus mode, the table of contents' proportional scroll) on the Read-along player milestone in Linear and the `idea/read-along-player` branch. This gap gets its note when the surface lands.
