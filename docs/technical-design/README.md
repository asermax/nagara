---
title: "Technical design"
summary: "Index of the notes about how the code works"
---

# Technical design

This folder holds how the code works. Each note explains one part of it; the reasoning behind a choice sits in a callout next to the mechanism it justifies. See [the docs charter](../README.md) for how a note is written.

## Reading order

Read these three in order since everything else depends on them:

1. [item-lifecycle](item-lifecycle.md): the four statuses on the item row, and the item Workflow that does all the work for one item in nine steps and restarts from the step that failed
2. [article-extraction](article-extraction.md): how a fetched article becomes the item's typed units, each carrying its display and spoken form
3. [read-along-timing](read-along-timing.md): how those paragraphs get contiguous timing windows

Then whatever you are touching.

## What notes exist

One row per note, kept by hand: adding a note here is part of writing it.

| Note | Explains |
|---|---|
| [item-lifecycle](item-lifecycle.md) | The item's four statuses on its D1 row and the item Workflow that moves it through them: nine steps inside one step wrapper, with describe running one concurrent child step per description; DomainQueue's per-domain lease; the recipe runtime and the Flue author and revision agents; and a retry that restarts the Workflow from the step that failed. |
| [article-extraction](article-extraction.md) | How the item Workflow fetches an article and turns the recipe's markdown units into the item's typed units: a spoken form derived from each unit's display, a drop for a unit with nothing to say, and the acquisition of the article's declared images through the Images binding. |
| [recipes](recipes.md) | How one agent-authored script per domain extracts the domain's articles into markdown units, its versioned record, how a URL matches to it, and how agents author and revise it. |
| [markdown-units](markdown-units.md) | What a unit's display markdown carries for each source element, and how the shared converter and the validator turn a recipe's declared elements into it. |
| [read-along-timing](read-along-timing.md) | The pause-fold rule that keeps per-paragraph timing windows contiguous, gapless, and exactly covering the audio. |
| [image-and-code-describer](image-and-code-describer.md) | Gemini through AI Gateway and its response cache: one generated sentence for a block a listener can't see, reused by the code path and the image path, floored and capped against one shared per-item budget. |
| [tts-service](tts-service.md) | Kokoro-82M on Modal, a separate deployable the item Workflow reaches through two web endpoints behind Modal's proxy auth: it starts a synthesis with a presigned PUT URL for the audio, then polls for the result. |
| [item-contract](item-contract.md) | The item routes plus /health, the item JSON, and the typed display unit whose spoken form is projected out at the response boundary. |
| [common-package](common-package.md) | The package both Workers build from: the shared types, the R2 key layout, presigning, the item row's reads and writes, the SQL migrations for D1 and the cassette replay library. |
| [persistence-and-storage](persistence-and-storage.md) | The item, recipe version and ledger rows in one D1 database both Workers share, with JSON `units` and `degradations` columns and hand-written SQL migrations; audio and images in one R2 bucket under separate key prefixes, delivered through presigned URLs. |
| [authentication](authentication.md) | A single API key is the user's identity and guards every item route; audio and images reach a client as a 307 to a presigned URL, and only a backend holds the key. |
| [deployment-and-ci](deployment-and-ci.md) | Three deployables: the API Worker and the pipeline Worker, deployed with wrangler in a fixed order after `common/`'s D1 migrations, and the TTS service on Modal; each tree runs its own path-filtered CI checks. |
| [local-development](local-development.md) | Both Workers running locally on one shared state folder with D1 and R2 on disk, calling the real Firecrawl and AI Gateway and a `modal serve` copy of the TTS app, with a quick tunnel and a local proxy for Modal's audio upload. |
| [invariants](invariants.md) | The ten rules the code obeys, and where each one is explained. |

## What has no note yet

Honest gaps, so nobody assumes coverage that is not there.

- **The read-along player.** Not yet built in `web/`, so there is no part to explain. Its mechanism facts are settled: the `requestAnimationFrame` highlight sync and the seek nudge in [read-along-timing](read-along-timing.md), the shape of the surface in [the listening experience](../product-design/listening-experience.md), and the rest (memoized per-paragraph render, `transform: scale` for focus mode, the table of contents' proportional scroll) on the Read-along player milestone in Linear and the `idea/read-along-player` branch. This gap gets its note when the surface lands.
