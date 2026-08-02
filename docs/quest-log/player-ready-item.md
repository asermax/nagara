---
title: "Player-ready item"
tags:
  - quest
summary: "Does a real push through enqueue → eager-generate → poll yield a player-ready item? Yes: trafilatura on a plain fetch handled every HTML fixture tried, including a JS-rendered Substack post, and zero-broker Modal spawn + lazy poll cleanly told a running job from a crashed one."
status: solved
kind: spike
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Player-ready item

## What

Serves [[audio-read-later-queue]], handing a public article URL to a private service and getting back listenable read-along audio. Ran before this lab existed, directly against `api/` and `tts/` at root, under nagara's original graduate-in-place convention (see [[quest-log/README|the quest log's]] "How we work" for why that convention was later reversed); there is no adventure branch to point at.

The unknowns it cleared:

- Can URL→paragraph extraction be made trustworthy enough that its boundaries can drive a highlight? Extraction quality is treated as a first-class part of the answer, not a given.
- Does the item shape carry everything a read-along player needs to read: per-paragraph timing, text, duration?
- Does an async-and-poll shape avoid pushing retry/backoff bookkeeping onto an agent client, and can a poll tell a running job from a dead one?
- Does the async layer need a broker and a worker process at this scale, or is the compute platform's own invocation primitives enough?

## Design

An agent `POST`s a URL with its API key; extraction yields clean paragraphs; the item generates eagerly (Modal `spawn()`) and reaches `ready` with Opus audio and paragraph boundaries that match the article; inputs that cannot be fetched surface as `failed` + `error`.

What got built, the cheapest thing that could answer the question: a FastAPI store + poll (`POST /items`, `GET /items/{id}`, `GET /items/{id}/audio`), one seeded API key as the single user, SQLite for items, audio as a local file; a `tts/` Modal service adapted from an existing working Kokoro-82M pipeline, changed to accept `paragraphs[]` and return per-paragraph `{index, start, end, text}` timing plus audio and duration, with GPU + memory snapshotting enabled and a reserved `voice="__raise__"` sentinel to force a crash through the real `FunctionCall.get()` path. No quota, no list endpoint: neither is exercised by the question.

Judged against five real articles from the owner's own reading list: a clean static blog, a magazine longread, a newsletter, a JS-rendered Substack post (expected to break a naive fetch), and a PDF (a fetchable URL that is not HTML).

### Acceptance criteria

Pre-registered 2026-07-17 before any of it was built; the numbered conditions below are the original disproof list, unedited. Disproven if any of:

1. a *fetchable* fixture's returned `paragraphs[]` merge, fragment, or garble the article's real structure (the split is rejected);
2. the item shape is missing a field the player's read operations need; checked against a pre-registered checklist: paragraph highlight needs per-paragraph `[start, end)` + `text`, click-to-seek needs `start`, a progress bar needs `duration`;
3. the async-and-poll interaction forces the client into retry/backoff/timeout bookkeeping that a block-until-ready call would eliminate, **or** polling cannot distinguish `generating` from a silently-dead job;
4. a forced Modal-side crash lands `ready` (or `failed` with an empty `error`) instead of `failed` with a populated `error`.

Task criteria: each fixture reaches a terminal state with monotonic, contiguous paragraph timing (final `end` ≈ audio duration); paragraph-split quality is validated against the real article structure (the load-bearing check); a forced Modal-side failure surfaces as `failed` with a populated error, distinguishable from a still-running `TimeoutError`; a `ready` item is scored against the player's actual read operations.

## Answer

### 2026-07-17: the mechanism holds before the judged sessions run

A pre-session probe against the real deployed service confirmed a running job returns `generating` (the `TimeoutError` path holds, not misclassified as failed) and the `voice="__raise__"` sentinel re-raises cleanly through `FunctionCall.get()` into `failed`. Cleared to run the judged sessions with the mechanism verified, not assumed.

### 2026-07-17: the HTML-versus-headless boundary sits further out than assumed

A basic `requests`+trafilatura fetch handled all four HTML fixtures, including the JS-heavy Substack post: it server-renders its content, so no headless browser was needed for any fixture in the set. The PDF cleanly failed the content-type gate at enqueue. Split-quality wrinkles were consistent and edge-only: the title echoed as paragraph zero in three of four articles, plus nav/boilerplate cruft ("Table of Contents", a lone "-", a footer donation paragraph, a sponsor aside, footnote glyphs); article *bodies* were cleanly segmented throughout.

### 2026-07-17: the item shape carried every field the player reads

Scored against a real `ready` item: `paragraphs[].{start, end, text}` present for highlight, `start` present for seek, `duration` present for progress, `audio_url` present, no missing or wrong field.

### 2026-07-17: graduate-in-place quietly absorbed production hardening inside the timebox

Under the project's original graduate-in-place convention, this experiment absorbed pydantic-settings, module packages, `APIKeyHeader` auth on all routes, ~17 tests, ruff/ty, and a dropped dependency, inside what was meant to be a spike timebox. That observation is what later reversed the project's spike convention; see [[quest-log/README|the quest log's]] "How we work".

**Cleared.** All four task criteria met and none of the four disproof conditions triggered: four of four HTML fixtures reached `ready` with playable Opus audio and monotonic, contiguous paragraph timing; the PDF clean-failed with a clear content-type error; paragraph-split quality was validated good; the item shape carried every field a read-along player reads; a forced Modal-side crash surfaced as `failed` with a populated error while a running job was never mis-flagged. Zero-broker Modal `spawn()` + lazy `get(timeout=0)` held in practice, and the pause-fold timing rule reconciled exactly with measured audio duration on real articles.

**Scope.** Self-use, on nagara only; one session against five real articles from the owner's own reading list; a single-user spike (one seeded key, no quota or multi-user). Establishes that the pipeline produces player-ready items for typical public HTML articles. Does not establish demand, generalization beyond these article types and sites, or multi-user behaviour. The audio and split artifacts this run produced were not kept, so what survives is the finding rather than the evidence for it. Re-checking any of the above means re-running the pipeline against the same five articles.

---

Related: [[quest-log/README|the quest log]] · [[audio-read-later-queue]] · [[item-lifecycle]] · [[article-extraction]] · [[read-along-timing]] · [[tts-service]] · [[item-contract]] · [[authentication]]
