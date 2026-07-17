# Feature Design — Enqueue-to-audio API

**Status**: ✓ current **Spec**: [feature-specs/enqueue-to-audio-api.md](../feature-specs/enqueue-to-audio-api.md) **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md) (the spike is reference material — this design is the durable description of the built system) **Decisions**: [ADR-001](../architecture/ADR-001-modal-tts-zero-broker-async.md), [ADR-002](../architecture/ADR-002-api-key-as-identity.md), [ADR-003](../architecture/ADR-003-sqlalchemy-sqlite-to-postgres.md), [ADR-004](../architecture/ADR-004-trafilatura-extraction-headless-deferred.md), [ADR-005](../architecture/ADR-005-python-toolchain.md), [DES-001](../design/DES-001-read-along-timing-windows.md)

How the backend spine turns a public article URL into a private, player-ready read-along audio item.

## Problem context

The feature must accept a URL and hand back, eventually, an item that a read-along player can consume with zero reshaping. Its shape is set by a few constraints:

- **Generation is slow and GPU-bound**, so enqueue cannot block until audio exists — the item must be produced eagerly in the background and observed later. Text-to-speech runs as a separate GPU service that the API invokes remotely (ADR-001).
- **Paragraph boundaries are the product's responsibility**, because they drive read-along highlighting — extraction must yield trustworthy paragraphs, not whatever the page happens to contain (ADR-004).
- **Items are private**: every route, including audio, is authenticated, and the credential is the user (ADR-002).
- **State must be durable** across the async gap between enqueue and completion (ADR-003).
- **Single-user for now**: no quota, no list, no multi-user identity — this is the spine other slices build on, not the whole product.

## Design overview

Six roles, split across two independently deployed processes — the API and the TTS service:

- **HTTP API** — three routes: enqueue an item, poll an item, fetch an item's audio. All are behind the auth guard.
- **Auth guard** — rejects any request without the valid credential, uniformly across the three routes (ADR-002).
- **Extraction service** (in the API) — fetches the URL and produces `(title, paragraphs[])`, or clean-fails on non-HTML (ADR-004).
- **TTS invocation client** (in the API) — spawns a remote synthesis call and later resolves it, translating the resolution into item state (ADR-001).
- **TTS compute** (separate deployable) — renders paragraphs to audio and produces the read-along timeline (DES-001). Not imported by the API; invoked remotely.
- **Persistence** — the item record (SQLite now, Postgres at graduation, via ORM — ADR-003) plus the audio stored as a file on disk.

```
        enqueue (URL, voice?)                    poll                     audio
              │                                   │                        │
              ▼                                   ▼                        ▼
   ┌───────────────────────── HTTP API  (auth guard on every route) ──────────────┐
   │  create item (generating)          load item                 load item        │
   │        │                              │                        │              │
   │        ▼                              ▼ if generating          ▼ if ready     │
   │   extract(URL) ──fail──▶ failed   resolve remote call      stream audio file  │
   │        │ ok                           │                                       │
   │        ▼                       ┌──────┼───────────┐                           │
   │   spawn remote synth ──────────┤ running│ crashed │ done                      │
   │        │  persist call handle  │  →gen  │ →failed │ →ready: store audio+timing │
   │        ▼                       └────────┴─────────┘                           │
   │   return accepted (generating)                                                │
   └──────────────┬────────────────────────────────────────────────┬─────────────┘
                  │ persist / load                                  │ write / read
                  ▼                                                 ▼
          item record (ORM)                                   audio file on disk
                  ▲ spawn / resolve
                  │  (remote, zero broker)
        ┌─────────┴──────────┐
        │  TTS compute        │  Kokoro-82M on GPU: paragraphs → audio + timeline (DES-001)
        │  (separate deploy)  │
        └────────────────────┘
```

## Modeling & data flow

**Item** is the single persisted entity. Fields: an id, the source URL, the extracted title, the status, the chosen voice, a creation timestamp, and — populated once ready — the audio duration, the audio format, and the read-along paragraph windows. It also holds the handle to the in-flight synthesis call and, on failure, the error. Audio bytes are **not** stored on the item; they live as a file on disk keyed by the item id, and the ORM row holds only metadata and the timing JSON (ADR-003).

**Status is a three-state machine**, eager from creation:

```
        create + extract ok + spawn ok
   ──────────────────────────────────────▶  generating
   generating  ──(poll: remote done)──────▶  ready
   generating  ──(poll: remote crashed)───▶  failed
   (create: extract fails | spawn fails)──▶  failed
```

There is no `queued` state: because generation starts eagerly on enqueue, the item is `generating` from the client's first observation.

**Flow, enqueue → ready:**

1. **Enqueue** creates the item as `generating`, then extracts the URL. If extraction fails (fetch error or non-HTML), the item is marked `failed` with the reason and returned — no synthesis is attempted. Otherwise the API spawns a remote synthesis call over the paragraphs and persists its handle. Enqueue returns the item immediately (accepted, `generating`).
2. **Poll** loads the item. If it is `generating` and has a call handle, the API resolves the remote call non-blockingly: *still running* leaves it `generating`; *crashed* transitions it to `failed` with the surfaced error; *done* stores the audio file and the timing, and transitions it to `ready`. The resolved item is returned.
3. **Audio** loads the item; if it is `ready`, its audio file is streamed with the stored format; otherwise the route reports not-available.

The resolve step is **lazy on poll** — there is no background sweeper. An item only advances when a client asks about it, which is exactly when the new state is needed.

## Key mechanisms

| Part | Mechanism | Serves |
|------|-----------|--------|
| Eager generation | Enqueue creates the item and kicks off synthesis in the same request, then returns without waiting | R1 |
| Async-and-poll lifecycle | Enqueue returns a non-terminal item; the client polls until terminal. State advances lazily on poll (ADR-001) | R2, R3 |
| Zero-broker remote synth | Spawn a remote call and persist its handle; resolve it non-blockingly on poll. *Still running* vs. *crashed* is read from the resolution outcome — no broker, no worker, no separate status tracking (ADR-001) | R2, R3 |
| Extraction | Fetch the URL, gate on content-type (non-HTML clean-fails), extract the main text, read the title, and trim edge cruft to clean body paragraphs (ADR-004) | R4 |
| TTS + timing | Kokoro-82M on GPU renders each paragraph and assembles the audio; timing follows the pause-fold rule so windows are contiguous and end at the audio duration (DES-001) | R5, R6, R7 |
| Read-along contract | The item's response exposes per-paragraph windows + text, total duration, status/error, and an audio link that is present only when ready | R5 |
| Uniform auth | A single credential header guards all three routes; absent/incorrect ⇒ unauthorized (ADR-002) | R8 |
| Persistence | The item is an ORM row (store graduates SQLite → Postgres); audio is a file on disk keyed by item id; each request uses a session that commits on success and rolls back on error (ADR-003) | R2 |
| Voice selection | Enqueue accepts an optional voice; absent ⇒ the configured default (carried on the item and passed to synthesis) | R9 |

## Key decisions

### Eager generation on enqueue (not a deferred queue)

- **Choice**: synthesis starts inside the enqueue request; the item is `generating` from first observation. No separate "start" step and no `queued` pre-state.
- **Evidence**: experiment 001.
- **Alternatives considered and not chosen**: a deferred queue where an item sits `queued` until a worker picks it up — not chosen; it adds a state and a scheduler for no benefit when the remote platform already runs the work asynchronously on spawn.
- **Consequences**: the client sees progress immediately; the lifecycle is a clean three-state machine. If a non-eager path (e.g. scheduled batch) is ever added, the `queued` state returns then, not now.

### Lazy resolution on poll (no background sweeper)

- **Choice**: an item advances from `generating` only when a client polls it; there is no background process reconciling in-flight calls.
- **Evidence**: experiment 001.
- **Alternatives considered and not chosen**: a background sweeper polling all in-flight calls — not chosen; unnecessary at this scale and it reintroduces a worker process the zero-broker approach (ADR-001) deliberately avoids.
- **Consequences**: no worker to run; state is computed exactly when observed. An item nobody polls stays `generating` in the record until someone asks — acceptable, since state is only needed when read.

### Audio stored as a file, not a database blob

- **Choice**: audio bytes are written to disk keyed by item id and streamed from there; the database row holds only metadata and the timing JSON.
- **Evidence**: experiment 001.
- **Alternatives considered and not chosen**: storing audio in the database — not chosen; multi-megabyte blobs bloat the row store and complicate the SQLite→Postgres graduation. (Object storage is the natural production home; a file on disk is the spike-stage stand-in.)
- **Consequences**: the audio route is a file stream; graduation to object storage is a localized change behind the same route.

## Decisions surfaced

- **ADR-001** — Modal-hosted TTS as a separate deployable with zero-broker async (spawn + lazy resolve). *Hard-to-reverse, project-wide.*
- **ADR-002** — API-key-as-identity auth (single-user, OAuth deferred). *Project-wide.*
- **ADR-003** — SQLAlchemy ORM over SQLite now, Postgres at graduation. *Project-wide storage boundary.*
- **ADR-004** — Server-side extraction with trafilatura; headless browser deferred. *Project-wide extraction foundation.*
- **ADR-005** — Python toolchain (uv/ruff/ty/pytest). *Project-wide standard.*
- **DES-001** — Read-along timing windows (pause-fold rule). *Repeatable producer/consumer contract.*

## System behavior

- **Happy path** — Enqueue an HTML article with a valid credential → item returned as `generating`. Poll while synthesis runs → `generating`. Poll after completion → `ready` with contiguous paragraph windows (last end == duration) and an audio link. Fetch audio → playable stream.
- **Non-HTML URL** — Enqueue a PDF (or other non-HTML) URL → the item fails at enqueue with an error naming the unsupported content type; no synthesis is attempted.
- **Fetch failure** — A URL that cannot be fetched or yields no article text → the item fails at enqueue with the reason.
- **Remote crash** — Synthesis crashes on the GPU host → the next poll surfaces `failed` with the remote error; a still-running job is never mis-reported as failed.
- **Poll while generating** — A poll during synthesis returns `generating` with no error and no blocking; the client simply polls again.
- **Audio before ready** — Fetching the audio route for a non-`ready` item → not-available; audio is exposed only once ready.
- **Missing/invalid credential** — Any route without the valid credential → unauthorized; no item data or audio is returned, including for the audio route.
- **Unknown item** — Polling or fetching audio for an unknown id → not-found.
- **Voice** — Enqueue with a voice uses it; without one, the configured default is used and recorded on the item.
