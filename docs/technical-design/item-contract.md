---
title: "Item contract"
tags:
  - technical-design
summary: "The three item routes plus /health, the item JSON, and why paragraphs[].text still means display markdown rather than spoken text."
---

# Item contract

The HTTP surface a client (Tachikoma today, a future web player eventually) actually reads and writes. Three routes behind the auth guard ([[authentication]]), plus one public liveness route.

## What it exposes

An `ItemResponse`, with a `Paragraph` per read-along window:

| Field | Answers |
|---|---|
| `id`, `url`, `title` | which item this is, and the article it points at |
| `status` | `generating`, `ready`, or `failed`: the state machine in [[item-lifecycle]] |
| `voice` | which Kokoro voice this item's audio uses, fixed at creation |
| `created_at` | when it was enqueued |
| `duration` | total audio length once `ready`; absent until then |
| `paragraphs[].{index, start, end, text}` | the read-along windows: `text` is display markdown, not spoken text, see the callout below |
| `error` | populated only when `status` is `failed` |
| `audio_url` (computed, not stored) | present only once `ready`, so a client never has to check status before deciding whether to trust the link |

## What each route does

| Route | Does |
|---|---|
| `POST /items` | Create an item from `{url, voice?}`. Returns `202` with the item, already `generating` or `failed` (see [[item-lifecycle]]). |
| `GET /items/{id}` | Poll. Resolves the in-flight synthesis call if the item is still `generating`, then returns the current item. `404` for an unknown id. |
| `GET /items/{id}/audio` | Serve audio for a `ready` item, via [[persistence-and-storage]]'s audio store. `404` if the item is not `ready`, has no audio format yet, or is unknown: no link is ever minted for a non-ready item. |
| `GET /items/{id}/images/{hash}` | Serve an image for the item, keyed by the content hash carried on an image unit. Minted fresh at read time — a file locally, a short-lived presigned URL in the bucket. `404` for an unknown item. An unknown *hash* answers differently per backend, which is deliberate; see below. Behind the same key as everything else. |
| `GET /health` | The one unauthenticated route; carries no item data. |

Voice selection: an enqueue request that names a voice uses it; one that omits it gets a voice chosen at random from a curated pool at creation time (`pick_voice()`, `VOICE_POOL` in `api/app/service/tts.py`), recorded on the item, and stable across every later poll.

> [!note] Why the field is still called `text`
> `paragraphs[].text` carries **display markdown**, not spoken text: the spoken form is an internal synthesis detail, joined onto the timing at finalize and then discarded rather than exposed (see [[article-extraction]]). The field kept its established name rather than being renamed to `display` or split into `display`/`spoken`, because no consumer needs the spoken form yet and renaming would churn every existing caller for no present gain. When a caption-export surface needs the spoken form, it gets its own field then.

## Image serving

`GET /items/{id}/images/{hash}` serves an image that belongs to the article. An image unit carries the content hash in its `image` field; a client reconstructs the path from the item id and the hash. The route requires the key, so invariant 4 holds uniformly.

> [!note] The URL is minted at read time, never persisted
> A presigned URL written into the row would be dead inside `s3_url_ttl` (3600s), and the unit list is persisted indefinitely. The store serves a `FileResponse` locally and a fresh presigned redirect in the bucket, reconstructing the object from the hash each request. The image object is keyed by a content hash of its re-encoded WebP bytes — not the item id, not the origin URL — so one image is stored once and dedupes across items and re-enqueues.

An unknown hash is the one place the two backends do not answer alike. Locally the store stats the file and raises the API's own `404`. In the bucket it mints the presigned URL without asking whether the object is there, so the client gets a `307` to a real signed URL that then answers `404` in the store's own format.

> [!note] Why the backends are allowed to disagree here
> Matching them means a `HEAD` per request, and this route is hot in a way the audio one is not: audio is one file per item fetched once, images are many per item fetched on every render. A round-trip per image to convert a store `404` into an API `404` is a poor trade when both already say not-found.
>
> The audio route has the same shape and does not have the same exposure, because it gates on `ready` and a recorded audio format first, so a missing object there is a genuine anomaly rather than a routine miss. Image serving has no equivalent gate on purpose, per the association note below.
>
> A caller that needs one uniform shape should treat any non-`200` from this route as absent rather than reading the body.

> [!warning] The item lookup checks existence, not association
> The route 404s an unknown item id but never checks that the hash belongs to that item, because the object is keyed by content hash alone so one image stores once and dedupes across items. Under today's single shared key that is not an escalation: there is nothing to reach the key does not already grant. Once per-key quota and API-key CRUD land, the item id in the path is decoration and one key can read another key's images by hash; whoever builds per-key auth must either check the hash against the item's own units or accept that images are shared across keys. See [[api-hardening]].

## What is not built yet

- **Quota and API-key CRUD.** No enforcement and no create/revoke route exist yet; see [[api-hardening]].
- **A list endpoint.** There is no `GET /items` today; a client tracks ids itself. Also [[api-hardening]].
- **Word-level timing.** Paragraph-level only, by design; see [[read-along-timing]].

---

Related: [[item-lifecycle]] · [[article-extraction]] · [[read-along-timing]] · [[authentication]] · [[persistence-and-storage]] · [[queue]]
