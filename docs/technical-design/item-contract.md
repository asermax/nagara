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
| `GET /health` | The one unauthenticated route; carries no item data. |

Voice selection: an enqueue request that names a voice uses it; one that omits it gets a voice chosen at random from a curated pool at creation time (`pick_voice()`, `VOICE_POOL` in `api/app/service/tts.py`), recorded on the item, and stable across every later poll.

> [!note] Why the field is still called `text`
> `paragraphs[].text` carries **display markdown**, not spoken text: the spoken form is an internal synthesis detail, joined onto the timing at finalize and then discarded rather than exposed (see [[article-extraction]]). The field kept its established name rather than being renamed to `display` or split into `display`/`spoken`, because no consumer needs the spoken form yet and renaming would churn every existing caller for no present gain. When a caption-export surface needs the spoken form, it gets its own field then.

## What is not built yet

- **Quota and API-key CRUD.** No enforcement and no create/revoke route exist yet; see [[api-hardening]].
- **A list endpoint.** There is no `GET /items` today; a client tracks ids itself. Also [[api-hardening]].
- **Word-level timing.** Paragraph-level only, by design; see [[read-along-timing]].

---

Related: [[item-lifecycle]] · [[article-extraction]] · [[read-along-timing]] · [[authentication]] · [[persistence-and-storage]] · [[queue]]
