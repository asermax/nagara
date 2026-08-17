---
title: "Build the pipeline steps"
tags:
  - quest
summary: "Implement the step-based pipeline and capability interfaces settled in pipeline-step-interfaces."
status: solved
kind: build
adventure:
blocked_by: []
priority: 2-soon
created: "2026-08-17"
---

# Build the pipeline steps

## What

Implement the shape settled in `pipeline-step-interfaces` (solved): capability interfaces
(Fetcher, Extractor, Describer, Synthesizer) and a step-based pipeline positioned by item
state, replacing the procedural `advance_queued_item` and the poll block in `get_item`. One
session's build. No schema change — per-step persistence moves when writes happen, not the
columns.

## Design

See `pipeline-step-interfaces` for the settled shape.

Five concretizations decided during the build:

- **Fetcher/Extractor are synchronous**, bridged through `run_in_threadpool` at the step, not
  `async def fetch`. It matches the codebase's bridge-a-sync-lib-at-its-call-site convention,
  and `test_extract` patches `app.service.extract.trafilatura`, so the fetch code has to stay
  in that module.
- **The concrete fetchers live beside their library** (`PlainFetcher` in `extract.py`,
  `FirecrawlFetcher` in `fallback.py`); only the `Fetcher` abstraction and the value types
  (`FetchedPage`, `FirecrawlUsage`) sit in the new `fetch.py`. Same reason: a test patches each
  library at its own module.
- **The escalation stays in `extract_with_fallback`**, the source composer `SourceStep` calls,
  above the pure fetchers and the one extractor — a named function rather than inlined in the
  step class.
- **`PipelineContext` copies the row's fields** rather than wrapping the ORM item: a step's
  working state runs ahead of the persisted row, and mutating the item in the queued phase
  would dirty it so a later autoflush slips an unguarded UPDATE past the `WHERE status='queued'`
  guard. The context stays pure data; the item stays pristine.
- **`ResolveStep` and `StoreStep` are two steps**, split on the `tts:` / `store:` prefix.

## Answer

Built on `adventure/pipeline-step-interfaces`. The procedural `advance_queued_item` and the
poll block collapse to one `pipeline.advance(item, db)` positioned by item state: four queued
steps (source, image, describe, spawn) driven by the background task, two generating steps
(resolve, store) driven by poll, each gating on the status it advances from. The capability
seams are real and used end to end: `PlainFetcher`/`FirecrawlFetcher` (`Fetcher`),
`TrafilaturaExtractor` (`Extractor`), `GeminiDescriber` (`Describer`), `ModalSynthesizer`
(`Synthesizer`). Per-step persistence writes `units` and `enriched_at` before spawn, so a
spawn or store crash now leaves a zero-cost-retryable row — an improvement over the old
all-or-nothing generating write, and the one behavior change (`test_late_task` updated).

Reaches: all 206 API tests green through cassettes and mocks, ruff and ty clean; `lifecycle.py`
dropped from ~200 lines to ~50. The real Modal / firecrawl / gemini path was **not** driven end
to end (no access in this environment) — only orchestration and persistence moved, every
extraction/describe/TTS internal is untouched, so audio output is unchanged.

Stops being true if the async-gap model changes — `streaming-paragraph-audio` would make
synthesis multi-result and break the single spawn → resolve handoff the two generating steps
assume.

**Lore still owed.** The technical-design notes (`item-lifecycle.md` above all, plus light
touches to `article-extraction`, `tts-service`, `the-describer`) still describe the superseded
procedural shape and must be brought back in line before this effort is struck.
</content>
