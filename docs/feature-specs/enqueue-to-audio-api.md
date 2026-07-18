# Feature Spec — Enqueue-to-audio API

**Status**: ✓ current **Roadmap**: [Milestone 1 — the backend spine](../planning/ROADMAP.md) **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md), `LEARNINGS.md` 2026-07-17 — 001

The backend spine of Nagara: the API that turns a public article URL into a private, player-ready read-along audio item. It is the surface Tachikoma pushes to and every future web surface consumes. What follows is the present intent of the feature — the behavior it guarantees and the boundaries it holds.

## User story

As an API consumer (an agent such as Tachikoma, or a future web client), I want to enqueue a public article URL and receive a private item that becomes player-ready read-along audio, so that I can push reading-list articles into a private audio queue without managing the generation myself.

## Requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| R1 | Enqueue a public article URL (with an optional voice) and get back a private item; generation begins immediately, without a separate trigger | Core goal | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R2 | The item is pollable and reaches a terminal state: `ready` (with playable audio and read-along timing) or `failed` (with a human-readable error) | Core goal | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R3 | Enqueue returns immediately rather than blocking until audio is ready; polling distinguishes *still generating* from *failed* without the client tracking retries or timeouts | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R4 | The URL is extracted into clean, trustworthy paragraphs whose boundaries match the article; a URL that is not a fetchable HTML article fails cleanly with a clear reason | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md), `LEARNINGS.md` 001 |
| R5 | A `ready` item carries everything a read-along player needs: per-paragraph timing windows with text, a total duration, and a link to the audio | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R6 | Paragraph timing windows are monotonic, non-overlapping, and contiguous, and the final window ends at the audio's total duration | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R7 | Audio is delivered as a playable stream | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R8 | Every item route — enqueue, poll, and audio — requires authentication; the credential identifies the user. A private item is never reachable without it; its audio is served only through a short-lived link that is minted solely to an authenticated caller and expires. (A public `/health` liveness route carries no item data.) | Must-have | [exp 001](../../experiments/001-player-ready-item/README.md) |
| R9 | The voice is selectable per item; when unspecified, a voice is chosen at random from a curated pool | Nice-to-have | [exp 001](../../experiments/001-player-ready-item/README.md) (selectability); New (random fallback) |

Requirements state WHAT is needed. Acceptance criteria below define HOW to verify each.

## Acceptance criteria

- **R1** — Given a valid API credential and a URL that fetches as an HTML article, When it is enqueued, Then an item is created and returned immediately in a non-terminal `generating` state, and generation is already underway (no separate start call).
- **R2** — Given an enqueued item, When it is polled after generation completes, Then it reports `ready` with playable audio and read-along timing; and Given an unknown item id, When it is polled (or its audio fetched), Then it is reported not-found.
- **R3** — Given an item still generating, When it is polled, Then it reports `generating` (not an error and not a block); and When the underlying generation has crashed — or its result cannot be persisted/stored — Then a poll reports `failed` with a populated, human-readable error — the two are distinguishable from the item alone, with no retry/backoff bookkeeping required of the client. Generation failure surfaces either at enqueue (when it cannot even begin — see R4) or on a later poll (when a running job crashes or its result cannot be finalized); in both cases the terminal item carries the error.
- **R4** — Given a URL that fetches as an HTML article, When it is enqueued, Then extraction yields clean body paragraphs (no echoed title, navigation labels, footnote glyphs, or punctuation-only artifacts) whose boundaries match the article; and Given a URL that cannot be turned into audio at enqueue — not fetchable, fetchable but not HTML (e.g. a PDF), or synthesis cannot be dispatched — When it is enqueued, Then the **enqueue response itself is the item already in `failed`** with a populated error (naming the unsupported content type for the non-HTML case), observable without a poll.
- **R5** — Given a `ready` item, When it is read, Then it exposes, for each paragraph, a timing window (`start`, `end`) and its `text`, plus the total audio `duration` and an audio link — sufficient for paragraph highlighting, click-to-seek, and a progress bar with no reshaping.
- **R6** — Given a `ready` item's paragraph windows, When they are inspected in order, Then each window's start equals the previous window's end (contiguous, non-overlapping, monotonic) and the last window's end equals the reported audio duration.
- **R7** — Given a `ready` item, When its audio route is called with a valid credential, Then it yields playable audio via a short-lived link a headerless client (a browser audio element) can follow; and Given an item that is not `ready` (or an unknown id), When its audio is requested, Then audio is refused as not-available and no link is minted.
- **R8** — Given a request with a missing or incorrect credential to any route (enqueue, poll, or audio), Then it is rejected as unauthorized and no item data or audio is returned.
- **R9** — Given an enqueue request that specifies a voice, When the item generates, Then that voice is used; and Given one that omits it, Then a voice chosen at random from a curated pool is recorded on the item at creation and used, staying stable across later polls.

## Open questions / unknowns

- **Browser audio delivery — server-side resolved.** The audio route mints a short-lived signed link to an authenticated caller, which a headerless browser audio element can then fetch directly; the store stays private. What remains is the web player's client-side integration (fetch the link with the credential, then feed the element) — that lives with the web-player slice, not here.
- **Extraction robustness beyond the tested article types.** Boundaries were validated on a clean blog, a magazine longread, a newsletter, and a JS-rendered Substack post. Genuinely client-rendered sites (no server-render) and prose-boilerplate stripping (footer/sponsor asides) are unresolved — captured in `BACKLOG.md`.

## Out of scope

- **Quota enforcement, a list endpoint, and API-key create/revoke** — deferred API furniture; not needed to prove or run the single-user pipeline (in `BACKLOG.md`, API-hardening pass).
- **Multi-user identity and OAuth** — single-user for now; a later slice.
- **Word-level timing** — paragraph-level only; word-level highlighting is deferred.
- **Headless-browser fetching** — not part of the pipeline; reached for only if a specific site demands it.
- **Caption export, audio caching by (url, voice), decay-based cleanup** — later ideas, not this feature.

## Dependencies

None — this is the spine every other slice depends on. (Roadmap ordering: [`docs/planning/ROADMAP.md`](../planning/ROADMAP.md).)
