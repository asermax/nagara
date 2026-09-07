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

A display unit is a pydantic discriminated union on `type`, one of `paragraph`, `code`, or `image`. Each variant carries its rendered markdown in `display`, its `type`, and an internal `spoken` form; an image unit adds `image`, a content hash. The persisted unit holds all of that; the wire element drops `spoken` and adds the timing window:

| Shape | Carries |
|---|---|
| persisted `Unit` | `type`, `display`, `spoken`, plus `image` on an image unit |
| wire `UnitResponse` | `index`, `type`, `display`, `start`, `end`, plus `image` on an image unit |

`units` is `null` until every window is timed, and carries the complete timed list from `ready` onward.

> [!NOTE] The spoken form never reaches a client
> `display` and `spoken` come from one markdown segmentation on one unit; the spoken form is a synthesis detail, joined onto the timing at finalize and then filtered out by the response model rather than exposed (see [article-extraction](article-extraction.md)). Projecting it out at the response boundary is the mechanism behind invariant 1's oldest clause: no client ever reads the spoken text, and the display form is never synthesized. A caption-export route that needs the spoken form gets its own field then; no consumer needs it today.

> [!NOTE] Why the list is held back until it is timed
> A wire element carries `start` and `end`, and timing only exists once synthesis finishes. Units are persisted at enqueue with `type`/`display`/`spoken` but no window, and enrichment writes them incrementally, so a partial, untimed list sits on the row while the item is `queued` or `generating`. Returning `null` until the list is timed keeps that partial state off the wire, so a client never renders half an article. Nothing is lost: a client polling a not-yet-`ready` item has no timeline to render against anyway.

## 🛣️ What each route does

| Route | Does |
|---|---|
| `POST /items` | Create an item from `{url, voice?}`. Returns `202` with the item at `queued`; a background task then fetches, segments, enriches, and spawns synthesis (see [item-lifecycle](item-lifecycle.md)). |
| `GET /items/{id}` | Poll. Resolves the in-flight synthesis call if the item is `generating`, and fails a `queued` item whose work age has passed the ceiling, then returns the current item. `404` for an unknown id. |
| `GET /items/{id}/audio` | Serve audio for a `ready` item, via [persistence-and-storage](persistence-and-storage.md)'s audio store. `404` if the item is not `ready`, has no audio format yet, or is unknown: no link is ever minted for a non-ready item. |
| `GET /items/{id}/images/{hash}` | Serve an image for the item, keyed by the content hash carried on an image unit. Minted fresh at read time: a file locally, a short-lived presigned URL in the bucket. `404` for an unknown item. An unknown *hash* answers differently per backend, which is deliberate; see below. Behind the same key as everything else. |
| `POST /items/{id}/retry` | Re-drive a `failed` item in place, resuming from the phase that failed. `202` with the item back at `queued`; `409` unless the item is `failed` and under the retry cap, `404` for an unknown id. See the section below and [item-lifecycle](item-lifecycle.md). |
| `GET /health` | The one unauthenticated route; carries no item data. |

Voice selection: an enqueue request that names a voice uses it; one that omits it gets a voice chosen at random from a curated pool at creation time (`pick_voice()`, `VOICE_POOL` in `api/app/service/tts.py`), recorded on the item, and stable across every later poll.

## 🖼️ Image serving

`GET /items/{id}/images/{hash}` serves an image that belongs to the article. An image unit carries the content hash in its `image` field; a client reconstructs the path from the item id and the hash. The route requires the key, so invariant 4 holds uniformly.

> [!NOTE] The URL is minted at read time, never persisted
> A presigned URL written into the row would be dead inside `s3_url_ttl` (3600s), and the unit list is persisted indefinitely. The store serves a `FileResponse` locally and a fresh presigned redirect in the bucket, reconstructing the object from the hash each request. The image object is keyed by a content hash of its re-encoded WebP bytes, not the item id or the origin URL, so one image is stored once and dedupes across items and re-enqueues.

An unknown hash is the one place the two backends do not answer alike. Locally the store stats the file and raises the API's own `404`. In the bucket it mints the presigned URL without asking whether the object is there, so the client gets a `307` to a real signed URL that then answers `404` in the store's own format.

> [!NOTE] Why the backends are allowed to disagree here
> Matching them means a `HEAD` per request, and this route is hot in a way the audio one is not: audio is one file per item fetched once, images are many per item fetched on every render. A round-trip per image to convert a store `404` into an API `404` is a poor trade when both already say not-found.
>
> The audio route has the same shape and does not have the same exposure, because it gates on `ready` and a recorded audio format first, so a missing object there is a genuine anomaly rather than a routine miss. Image serving has no equivalent gate on purpose, per the association warning below.
>
> A caller that needs one uniform shape should treat any non-`200` from this route as absent rather than reading the body.

> [!WARNING] The item lookup checks existence, not association
> The route 404s an unknown item id but never checks that the hash belongs to that item, because the object is keyed by content hash alone so one image stores once and dedupes across items. Under today's single shared key that is not an escalation: there is nothing to reach the key does not already grant. Per-key quota and API-key management are not built yet; once they are, the item id in the path is decoration and one key can read another key's images by hash, so whoever builds per-key auth must either check the hash against the item's own units or accept that images are shared across keys.

## 🔁 Retry

`POST /items/{id}/retry` re-drives a failed item in place rather than re-enqueuing the URL, so a synthesis crash on someone else's GPU costs nothing to recover from. It refuses anything but a `failed` item, and a `failed` item past the retry cap, with `409`; `404` for an unknown id. An accepted retry sets the item back to `queued`, rewrites `queued_at`, advances `retry_count`, clears the old error, and hands the item to the queued lifecycle task, the same task enqueue uses.

What that task does depends on what the previous run left on the row, keyed on `enriched_at`:

| Row at retry | What the task does | Cost |
|---|---|---|
| `enriched_at` set | re-spawn synthesis from the units on the row, straight to `generating` | no fetch, no describe |
| `enriched_at` null, units present | back to `queued`, re-enrich the units still missing spoken text | one fetch, partial describe |
| `enriched_at` null, no units | back to `queued`, full enrichment | full cost |

The common case is the first row: enrichment already completed, so a retry re-spawns and nothing else. `queued_at` is rewritten on every attempt, which is why the queued ceiling measures from it rather than from `created_at`.

> [!NOTE] The middle row is the intended shape
> Enrichment is fetch and segment today, which is all-or-nothing, so both `enriched_at`-null rows re-extract in full. The task branches on `enriched_at` alone. Per-unit resume is the shape the describer's per-unit enrichment keys on, and the row is written that way rather than the way it currently degrades.

> [!NOTE] Double-submitting is refused by the write, not by the read
> The transition is one conditional `UPDATE` gating on status still `failed` and `retry_count` under the cap, incrementing the count in SQL. A rowcount of zero is the `409`. Reading the row first and then writing would let two concurrent retries both pass the guard, which costs two Modal spawns for one item and increments the count once, so the cap would read tighter than it is. The pre-read only picks which refusal message to send.

> [!NOTE] Why the cap is local and quota is not
> The per-item retry cap (`retry_max`, default 3) is a cheap local bound on the worst case: a flapping item spends at most a few synthesises before it stays failed. Broader per-key and quota enforcement is deliberately not built here. The cap does not need the full hardening apparatus, and building half of one here would be worse than either.

## ⏩ What is not built yet

- **Quota and API-key management.** No enforcement and no create/revoke route exist yet.
- **A list endpoint.** There is no `GET /items` today; a client tracks ids itself.
- **Word-level timing.** One window per unit, not per word, by design; see [read-along-timing](read-along-timing.md).

---

Related: [item-lifecycle](item-lifecycle.md) · [article-extraction](article-extraction.md) · [read-along-timing](read-along-timing.md) · [authentication](authentication.md) · [persistence-and-storage](persistence-and-storage.md) · [queue](../product-design/queue.md)
