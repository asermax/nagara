---
title: "Item lifecycle"
tags:
  - technical-design
summary: "The item's four-state machine: enqueue commits a queued row, a mortal in-process task enriches and spawns to generating, poll resolves Modal to ready or failed, and retry re-drives from the phase that failed."
---

# Item lifecycle

An item is the single persisted entity nagara has: the record of one `enqueue(url, voice?)` call, from creation through to playable audio or a clear failure. This note covers the four-state machine and the three routes plus one background task that drive it; [[article-extraction]] covers what the enrichment task does to a URL and [[read-along-timing]] covers what the TTS service hands back.

## What it exposes

The `Item` row, one per `enqueue` call, with `status` one of `queued` / `generating` / `ready` / `failed`:

| Field | Answers |
|---|---|
| `id` | the item's identity: `"itm_"` plus 8 hex characters |
| `url`, `title` | which article this item is for; `title` fills once extraction runs |
| `voice` | which Kokoro voice this item's audio uses, fixed at creation |
| `created_at` | when it was enqueued; never moves |
| `queued_at` | when the current attempt entered the queue: set in the enqueue write and rewritten on every retry. The ceiling measures work age from this, not from `created_at` |
| `enriched_at` | set once every unit has resolved: the flag that enrichment finished and a retry can re-spawn without re-enriching |
| `retry_count` | how many times this item has been re-driven; bounds re-spend against `retry_max` |
| `duration`, `audio_format` | populated once `ready` |
| `units` | the typed display/spoken/timing units, written at the `generating` transition and timed at `ready`; see [[article-extraction]] and [[item-contract]] |
| `degradations` | per-unit enrichment failures that did not fail the item; null when the enrichment was clean |
| `error` | populated only when `status` is `failed` |
| `modal_call_id` | the in-flight synthesis call's handle, resolved on poll |

Audio bytes are never a column on this row; they live in the store described in [[persistence-and-storage]], keyed by item id.

## How an item advances

```mermaid
stateDiagram-v2
    [*] --> queued: enqueue, 202
    queued --> generating: task fetched, segmented, enriched, spawned
    queued --> failed: task caught an error
    queued --> failed: poll, queued_at past the ceiling
    generating --> ready: poll, remote done, stored
    generating --> failed: poll, remote crashed
    generating --> failed: poll, store or persist fails
    failed --> queued: retry, item failed and under the cap
    ready --> [*]
    failed --> [*]
```

**Enqueue** commits the item as `queued`, with `queued_at` set in the same write, then schedules `advance_queued_item` as a `BackgroundTasks` handler and returns `202` immediately. The task opens its own session, so the row must be committed before it is scheduled; the response is serialized from the queued row, so a client sees `queued` on the `POST` and `generating` on the following poll.

**The background task** does the work that cannot happen inside a request: it fetches and segments the URL ([[article-extraction]]), enriches the units, then spawns a remote synthesis call over the derived spoken paragraphs and persists its handle (`modal_call_id`) in the same write that moves the item to `generating`. Any error along the way fails the item with a prefixed reason (see [[#What a failure names]]).

**Poll** loads the item and advances it in place. It applies the queued ceiling first, then resolves an in-flight Modal call:

```mermaid
flowchart TD
    P["poll: resolve modal_call_id"] --> R{"FunctionCall.get(timeout=0)"}
    R -->|TimeoutError| G["stays generating"]
    R -->|re-raised exception| F["failed, error recorded"]
    R -->|result| S["store_result: audio + timing"]
    S -->|ok| Y["ready"]
    S -->|raises| F
```

*Still running* and *crashed* are read directly from that resolution outcome: a timeout means running, a re-raised remote exception means the job crashed, and the two are never confused. *Done* stores the audio and the joined timing (see [[article-extraction]]'s index join) and transitions the item to `ready`; if that store or persistence step itself fails, the item transitions to `failed` with a readable error rather than being left stuck `generating`.

**Retry** (`POST /items/{id}/retry`) moves a `failed` item back to `queued` and re-schedules the same task; the section below covers it.

## Why `queued` and `generating` are separate states

The two phases have different physics, and the state names carry that distinction to the client.

Enrichment runs **in the API process**, as the `BackgroundTasks` handler. It is mortal: a redeploy or a container recycle kills it mid-flight, and an item stranded at `queued` has no way to finish on its own. Synthesis runs **on Modal**. Once spawned it survives a redeploy of the API, which is exactly why resolving it lazily on poll works across restarts.

So a `queued` item is in a strandable phase and a `generating` item is not. A client that could not tell them apart could not tell a phase that needs the ceiling to rescue it from one that recovers itself. The staleness rule would also have to infer the phase from whether `modal_call_id` happens to be set, instead of reading it off the status.

> [!note] Why the item is `queued` before it is `generating`
> Enqueue returns before synthesis starts because enrichment is real work with nowhere else to live: it fetches, segments and describes inside the API process, and that takes longer than a request should hold open. The `queued` state is the name of that in-process phase, and it exists precisely because the work is mortal and needs a recovery path the durable Modal phase does not.

> [!info] Considered and not chosen: one combined in-flight state
> Collapsing `queued` and `generating` into a single "working" status removes a column value but costs the one distinction that matters: a client, and the staleness rule, can no longer tell a strandable phase from an unstrandable one. The two states are kept because the two phases fail and recover differently, not because a client wants a finer progress bar.

## Deferred work is mortal, and the ceiling recovers it

The task's mortality is the price of running deferred work inside the API process instead of a worker, and two mechanisms pay it.

**The queued ceiling.** Poll fails a `queued` item once its work age passes `NAGARA_QUEUED_CEILING_SECONDS` (default 300), with `enrichment: no result after 300s`. Work age is `now - queued_at`, never `now - created_at`: `created_at` never moves, so measuring from it would fail a just-retried item instantly and turn retry into a no-op that reports failure. `queued_at` is set in the enqueue write, so even a row stranded before its task ever ran carries a clock the ceiling can read.

**Every task write is conditional on the item still being `queued`.** The writes go through `_write_if_queued`, a single `UPDATE ... WHERE status = 'queued'` that checks rowcount. If a slow-but-alive task finishes a minute after poll already tripped the ceiling and marked the item `failed`, its `generating` write matches zero rows and the task abandons, committing nothing further. A late task can never resurrect a failure a client has already observed. Nothing is lost either: the units the task wrote before the failure stay on the row, so a retry resumes from them.

> [!warning] A late task must not overwrite a failed row
> The subtle case is a container that was slow rather than dead. Without the conditional write, its finishing `UPDATE` would stamp `generating` over the `failed` a poll already surfaced, and a client that surfaced the failure would see the item silently un-fail. The `WHERE status = 'queued'` guard is what forecloses that. SQLite reports changed rows rather than matched rows, which is reliable here because every task write moves at least one column off its previous value.

> [!note] Why nothing sweeps in the background
> Both the Modal resolution and the ceiling are computed on poll, when a client asks. An item nobody polls simply stays where the last write left it, which is acceptable because the state is only needed at the moment it is read. Nothing runs on a timer scanning for work to advance.

> [!info] Considered and not chosen: a background sweeper polling all in-flight calls
> A sweeper that walked every `queued` and `generating` row would reintroduce a second process the zero-broker approach in [[tts-service]] deliberately avoids, for no benefit at this scale. State computed on poll is enough, because poll is exactly when the new state is needed.

## Retry resumes from the phase that failed

`POST /items/{id}/retry` re-drives a `failed` item in place, so a synthesis crash on someone else's GPU costs nothing to recover from. It returns `202` and hands the item to the same task enqueue uses; [[item-contract]] carries the route and wire detail.

**Only a `failed` item under the cap is retryable.** `queued`, `generating` and `ready` all return `409`, and so does a `failed` item at or past `retry_max` (default 3). A stranded item needs no special case: the ceiling converts it to `failed` first, which is the whole reason the ceiling exists rather than being a nicety.

The task branches on `enriched_at`, which is why the enqueue and retry paths share one handler:

| Row at retry | What the task does | Cost |
|---|---|---|
| `enriched_at` set | re-spawn synthesis from the units on the row, straight to `generating` | no fetch, no describe |
| `enriched_at` null, some units present | back to `queued`, re-enrich the units still missing spoken text | one fetch, partial describe |
| `enriched_at` null, no units | back to `queued`, full enrichment | full cost |

The common case is the first row: enrichment already completed, so retry re-spawns and nothing else. `queued_at` is rewritten on every attempt, which is why the ceiling measures from it.

> [!note] Retry does not re-fetch when enrichment completed
> Re-fetching would not reliably reproduce the first extraction: firecrawl's output is non-deterministic, measured at a 5x spread on the same URL minutes apart. So retry resumes from the stored units rather than re-deriving them, which means it cannot repair an item whose stored extraction was wrong on a 200-status error page; that is [[trustworthy-extraction]]'s force-restart to design, not something half-built here.

> [!note] The claim that stops two concurrent retries
> The `failed → queued` move is one conditional `UPDATE` gating on status still `failed` and `retry_count` under the cap, incrementing the count in SQL. Two concurrent retries cannot both win: only the first finds the preconditions met, the second lands zero rows and the route refuses it with `409`. A read-then-write would let both pass, spawning two Modal jobs for one item with the second orphaned and incrementing the count once, so the cap would read tighter than it is. The pre-read only picks which refusal message to send.

## What a failure names

Every `failed` item carries an `error` whose prefix names the phase that failed, so a reader can place a failure without a stack trace:

| Prefix | Phase |
|---|---|
| `fetch:` | fetching the URL, or firecrawl unreachable |
| `extraction:` | segmenting the fetched HTML into units |
| `enrichment:` | describing images and code in the API process, or the ceiling firing |
| `spawn:` | handing the spoken paragraphs to Modal |
| `store:` | writing the finished audio and timing on finalize |
| `tts:` | synthesis crashing on the GPU host, surfaced on poll |

The first five are set inside the task; `store:` and `tts:` are set on poll. A systemic failure at any of these phases fails the item.

> [!note] A per-unit degradation is not a failure
> Enrichment distinguishes a systemic failure from a single unit that could not be described. A failed image fetch or a failed describe call for one unit is recorded in `degradations` and the item still reaches `ready`; only an exception that stops the whole enrichment phase fails the item with the `enrichment:` prefix. So `degradations` is populated on items that succeeded, and `error` only on items that did not.

## Async endpoints over bridged sync libraries

Every endpoint is `async def` over an `AsyncSession`, so an enrichment task can fan its image fetches and describe calls out concurrently. The three libraries that stay synchronous each block the single event loop if called directly, so each is bridged through `run_in_threadpool` at its call site:

| Library | Call | Why it blocks |
|---|---|---|
| trafilatura | fetch and extract | a network fetch plus a CPU-bound extract |
| boto3 | the audio store's `store` | a synchronous S3 client |
| Modal client | `spawn_synthesis`, `poll_synthesis` | a synchronous remote call |

The database URL stays the logical sync-dialect one and is mapped onto the matching async driver at runtime (`asyncpg` for Postgres, `aiosqlite` for SQLite), because Alembic drives the sync driver from the same setting; see [[persistence-and-storage]].

> [!warning] A new sync library called from a route without the bridge blocks the loop, silently
> A blocked event loop still returns correct answers, just serialized, so nothing in the suite catches it. Any new synchronous, blocking call from an `async def` must go through the threadpool bridge.

## Failure paths

- **Non-HTML URL**: enqueuing a PDF or anything else non-HTML fails in the task with `fetch:` naming the unsupported content type; no synthesis is attempted.
- **Fetch failure**: a URL that cannot be fetched, or yields no article text, fails in the task with the `fetch:` or `extraction:` reason.
- **Stranded task**: the container dies mid-enrichment; the next poll past the ceiling fails the item with `enrichment: no result after 300s`, and a retry re-drives it.
- **Remote crash**: synthesis crashes on the GPU host; the next poll surfaces `failed` with the `tts:` error, and a still-running job is never mis-reported as failed.
- **Storage or persistence failure on finalize**: synthesis completes, but writing the audio or persisting the item fails; the poll surfaces `failed` with a `store:` error rather than leaving the item stuck `generating`.

> [!warning] Extraction can succeed on the wrong thing
> A URL serving a 200-status error page (a GitHub Pages 404, say) extracts cleanly, generates audio, and reaches `ready`: the worst failure mode, because it looks like a working item and the status is never `failed`. See [[trustworthy-extraction]].

## What is not built yet

Quota enforcement and a `GET /items` list endpoint are deferred furniture, not part of this lifecycle; see [[item-contract]]'s "what is not built yet" and the [[api-hardening]] work item. The spawn-failure branch has no covering test at the endpoint level; see [[test-spawn-failure-path-at-endpoint]].

---

Related: [[article-extraction]] · [[tts-service]] · [[item-contract]] · [[persistence-and-storage]] · [[authentication]] · [[invariants]]
