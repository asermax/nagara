---
title: "Item contract"
summary: "The item routes plus /health, the item JSON, and the typed display unit whose spoken form is projected out at the response boundary."
created: "2026-07-29"
---

# Item contract


## 🔭 Overview

The HTTP routes and JSON a client (Tachikoma today; the read-along player, not yet built in `web/`, later) reads and writes. The item routes all sit behind the auth guard ([authentication](authentication.md)), plus one public liveness route.


## ♠️ What it exposes

An `ItemResponse`, its `units` list carrying one `UnitResponse` per read-along window once timed:

| Field | Answers |
|---|---|
| `id`, `url`, `title` | which item this is, and the article it points at |
| `status` | `queued`, `generating`, `ready`, or `failed`: the state machine in [item-lifecycle](item-lifecycle.md) |
| `voice` | which Kokoro voice this item's audio uses, fixed at creation |
| `created_at` | when it was enqueued |
| `duration` | total audio length once `ready`; absent until then |
| `units[]` | the read-along list, one element per display unit; `null` until every window is timed, see below |
| `error` | populated only when `status` is `failed` |
| `audio_url` (computed, not stored) | present only once `ready`, so a client never has to check status before deciding whether to trust the link |

A display unit is a discriminated union on `type`, one of `paragraph`, `code`, or `image`, declared as a TypeScript type in [common/](common-package.md) so the API Worker and the pipeline Worker build against the same shape; the type is checked when each Worker builds, not at runtime. Each variant carries its rendered markdown in `display`, its `type`, and an internal `spoken` form; an image unit adds `image`, a content hash. The persisted unit holds all of that; the wire element drops `spoken` and adds the timing window:

| Shape | Carries |
|---|---|
| persisted `Unit` | `type`, `display`, `spoken`, plus `image` on an image unit |
| wire `UnitResponse` | `index`, `type`, `display`, `start`, `end`, plus `image` on an image unit |

`units` is `null` until every window is timed, and carries the complete timed list from `ready` onward.

> [!NOTE] The spoken form never reaches a client
> `display` and `spoken` come from one markdown segmentation on one unit; the spoken form is a synthesis detail, joined onto the timing at finalize and then filtered out by the response model rather than exposed (see [article-extraction](article-extraction.md)). Projecting it out at the response boundary is the mechanism behind invariant 1's oldest clause: no client ever reads the spoken text, and the display form is never synthesized. A caption-export route that needs the spoken form gets its own field then; no consumer needs it today.

> [!NOTE] Why the list is held back until it is timed
> A wire element carries `start` and `end`, and timing only exists once synthesis finishes. The item Workflow's recipe step writes the units into the row with `type`/`display`/`spoken` but no window, and the images and describe steps rewrite them, so a partial, untimed list sits on the row while the item is `queued` or `generating`. Returning `null` until the item is `ready` keeps that partial state off the wire, so a client never renders half an article. Nothing is lost: a client polling a not-yet-`ready` item has no timeline to render against anyway.

## 🛣️ What each route does

| Route | Does |
|---|---|
| `POST /items` | Create an item from `{url, voice?}`. Writes the item row at `queued`, then creates the item's Workflow instance with the item id, and returns `202` with the item at `queued`; the item Workflow does the rest (see [item-lifecycle](item-lifecycle.md)). When creating the instance fails, the API writes the item as `failed` with that error and returns it; a retry creates the instance. |
| `GET /items/{id}` | Poll. Reads the item row and returns the current item; it never reads the Workflow instance. Queues again an item that has been `queued` for more than 15 minutes. One conditional write claims the row and rewrites `queued_at`, so concurrent polls queue the item once. The API then restarts the item's instance from the step `current_step` names, or creates it with the item id when the row holds no instance id (see [item-lifecycle](item-lifecycle.md)). When that throws, the API logs the error and returns the item as it is, and the next poll 15 minutes later tries again. The re-queue does not count toward the retry cap. `404` for an unknown id. |
| `GET /items/{id}/audio` | Serve audio for a `ready` item: a `307` to a GET URL for the item's audio key in the R2 bucket, signed for one hour (see [persistence-and-storage](persistence-and-storage.md)). `404` if the item is not `ready`, has no audio format yet, or is unknown: no link is ever minted for a non-ready item. |
| `GET /items/{id}/images/{hash}` | Serve an image for the item, keyed by the content hash carried on an image unit. A `307` to a GET URL for the hash's key in the R2 bucket, signed fresh at read time for one hour. `404` for an unknown item. An unknown *hash* gets the `307` too, and R2 answers the signed URL with its own `404`; see below. Behind the same key as everything else. |
| `POST /items/{id}/retry` | Re-drive a `failed` item in place, restarting its Workflow instance from the step that failed. `202` with the item back at `queued`, or with the item `failed` again when the restart throws; `409` unless the item is `failed` and under the retry cap, `404` for an unknown id. See the section below and [item-lifecycle](item-lifecycle.md). |
| `GET /health` | The one unauthenticated route; carries no item data. |

Voice selection: an enqueue request that names a voice uses it; one that omits it gets a voice chosen at random from a curated pool at creation time, recorded on the item, and stable across every later poll.

The `url` string reaches the pipeline as given: nothing at the route or the schema validates it, and the first thing that can refuse it is the item Workflow's fetch step, which fails the item when Firecrawl returns nothing at all; the item's `error` is the fetch step's own error and `current_step` names `fetch`.

## 🖼️ Image serving

`GET /items/{id}/images/{hash}` serves an image that belongs to the article. An image unit carries the content hash in its `image` field; a client reconstructs the path from the item id and the hash. The route requires the key, so invariant 4 holds uniformly.

> [!NOTE] The URL is minted at read time, never persisted
> A presigned URL written into the row would be dead an hour after it is signed, and the unit list is persisted indefinitely. The API Worker signs a fresh URL on every request with its own R2 API token, building the object key from the hash through the key function in [common/](common-package.md). The image object is keyed by its content hash, not the item id or the origin URL, so one image is stored once and dedupes across items and re-enqueues.

An unknown hash is the one miss the API does not answer itself. The API Worker signs the URL without asking whether the object is there, so the client gets a `307` to a real signed URL that then answers `404` in R2's own format.

> [!NOTE] Why the route does not check the object first
> Answering the API's own `404` means a `HEAD` per request, and this route is hot in a way the audio one is not: audio is one file per item fetched once, images are many per item fetched on every render. A round-trip per image to convert an R2 `404` into an API `404` is a poor trade when both already say not-found.
>
> The audio route has the same shape and does not have the same exposure, because it gates on `ready` and a recorded audio format first, so a missing object there is a genuine anomaly rather than a routine miss. Image serving has no equivalent gate on purpose, per the association warning below.
>
> A caller that needs one uniform shape should treat any non-`200` from this route as absent rather than reading the body.

> [!WARNING] The item lookup checks existence, not association
> The route 404s an unknown item id but never checks that the hash belongs to that item, because the object is keyed by content hash alone so one image stores once and dedupes across items. Under today's single shared key that is not an escalation: there is nothing to reach that the key does not already grant. Per-key quota and API-key management are not built yet; once they are, the item id in the path is decoration and one key can read another key's images by hash, so whoever builds per-key auth must either check the hash against the item's own units or accept that images are shared across keys.

## 🔁 Retry

`POST /items/{id}/retry` re-drives a failed item in place rather than re-enqueuing the URL. It refuses anything but a `failed` item, and a `failed` item past the retry cap, with `409`; `404` for an unknown id. An accepted retry writes `queued`, rewrites `queued_at`, increments `retry_count` and clears the old error in one conditional write, then restarts the item's existing Workflow instance from the step named in `current_step`, or creates it with the item id when the row holds no instance id. The steps before it do not run again. A retry whose failed step is `recipe` or `release` restarts from `lease` instead, so the item asks for its domain's lease again and the recipe step reads the domain's current recipe. The Workflow moves the item to `generating` once it holds the lease, as on its first run; [item-lifecycle](item-lifecycle.md) carries the steps and what each one costs.

When the restart or the create throws after the claim, the route writes the item back to `failed` with that error and answers `202` with the failed item. The retry stays counted toward the cap.

> [!NOTE] Double-submitting is refused by the write, not by the read
> The transition is one conditional `UPDATE` gating on status still `failed` and `retry_count` under the cap, incrementing the count in SQL. A rowcount of zero is the `409`. Reading the row first and then writing would let two concurrent retries both pass the guard, which restarts one instance twice and increments the count once, so the cap would read tighter than it is. The pre-read only picks which refusal message to send.

> [!NOTE] Why the cap is local and quota is not
> The per-item retry cap (`retry_max`, default 3) is a cheap local bound on the worst case: a flapping item spends at most a few synthesises before it stays failed. Broader per-key and quota enforcement is deliberately not built here. The cap does not need the full hardening apparatus, and building half of one here would be worse than either.

## ⏩ What is not built yet

- **Quota and API-key management.** No enforcement and no create/revoke route exist yet.
- **A list endpoint.** There is no `GET /items` today; a client tracks ids itself.
- **Word-level timing.** One window per unit, not per word, by design; see [read-along-timing](read-along-timing.md).

---

Related: [item-lifecycle](item-lifecycle.md) · [common-package](common-package.md) · [article-extraction](article-extraction.md) · [read-along-timing](read-along-timing.md) · [authentication](authentication.md) · [persistence-and-storage](persistence-and-storage.md) · [queue](../product-design/queue.md) · [markdown-units](markdown-units.md)
