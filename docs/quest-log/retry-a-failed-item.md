---
title: "Retry a failed item"
tags:
  - quest
summary: "POST /items/{id}/retry re-drives a failed item, resuming from the phase that failed, so a synthesis crash costs nothing to recover from."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 2-soon
created: "2026-08-02"
---

# Retry a failed item

## What

An item failed. Today the only recourse is enqueueing the URL again, which loses the id and re-spends everything. `POST /items/{id}/retry` re-drives the item in place, resuming from whatever phase failed.

The common case is a crash on someone else's GPU, and that one costs nothing: enrichment already completed, so retry re-spawns synthesis and nothing else.

## Design

### The route

`POST /items/{id}/retry`, returning `202` and an `ItemResponse`. Per `CLAUDE.md` a new route owes an endpoint module, a pydantic schema, and a section in [[item-contract]].

### What is retryable

**Only a `failed` item, and only while `retry_count < NAGARA_RETRY_MAX` (default 3).** `queued`, `generating` and `ready` all return `409`, and so does an item past the cap.

A stranded item needs no special case, because [[queued-item-lifecycle]]'s five-minute ceiling converts it to `failed` first. That is the whole reason the ceiling exists rather than being a nicety.

Double-submitting is safe by construction: the second call finds a non-`failed` status.

### Retry resumes, keyed on `enriched_at`

| Row state | What retry does | Cost |
|---|---|---|
| `enriched_at` set | spawn synthesis, straight to `generating` | zero credits, zero describe calls |
| `enriched_at` null, some units present | back to `queued`, re-enrich only units still missing spoken text | one fetch, partial describe calls |
| `enriched_at` null, no units | back to `queued`, full enrichment | full cost |

`queued_at` is rewritten on every retry, which is why the ceiling measures from it rather than from `created_at`.

There is no describer cache, so the units a partial retry re-describes bill again. Per-row resume is what handles the common case; a cache would only have helped a total-loss retry, and defending against that with a cache is the wrong tool. The retry-count cap is the local bound instead.

### Retry does not re-fetch when enrichment completed

Deliberate, and load-bearing for two reasons.

It means retry **cannot repair an item whose stored extraction was wrong**. The item that reached `ready` on a 200-status error page is [[trustworthy-extraction]]'s problem, and a force-restart path is that quest's to design rather than something half-built here.

And re-fetching would not reliably reproduce what was extracted the first time anyway. Firecrawl's output is non-deterministic, measured at a 5x spread on the same URL minutes apart. This reasoning belongs in [[item-lifecycle]] as a stated *why*, not as an incidental.

### Why the cap is here and quota enforcement is not

The per-item retry-count cap is a cheap local bound on the worst case. Broader per-key and quota enforcement stays with [[api-hardening]], deliberately: the retry cap does not need the full hardening apparatus, and building half of one here would be worse than either.

### How it is verified

Seam 1, the HTTP surface. All three resume paths, the `409` on each non-retryable status, the `409` past the cap, and `queued_at` moving on each attempt.

The zero-cost path is the one worth asserting hardest: a retry with `enriched_at` set must issue no fetch and no describe call at all, which under cassettes means no cassette interaction.

## Answer

Built. `POST /items/{id}/retry` re-drives a `failed` item in place, returning `202`, and refuses anything else with `409`. The task branches on `enriched_at`: set means re-spawn synthesis from the units already on the row, with no fetch and no describe call at all.

**The defect found in review.** The transition was a read-then-write, which two concurrent retries both pass. That schedules two tasks, spawns two Modal jobs for one item with the second orphaned, and increments `retry_count` once because both computed `old + 1` from the same read — so the cap read tighter than it was. It is now a single conditional `UPDATE` gating on status and the cap, incrementing in SQL, with rowcount zero as the `409`. The test that covers it forces the interleaving with a barrier and asserts the spawn count; it was confirmed to fail against the old code.

**How far it reaches.** No migration: `retry_count` shipped as an unused column with [[queued-item-lifecycle]] and this is what starts writing it. The middle resume row is the shape rather than today's behaviour — enrichment is all-or-nothing until the describer quests land, so both `enriched_at`-null rows re-extract in full.

**What would make it stop being true.** Retry deliberately does not re-fetch when enrichment completed, so it cannot repair an item whose stored extraction was wrong; that is [[trustworthy-extraction]]'s.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[queued-item-lifecycle]] · [[item-contract]] · [[item-lifecycle]] · [[api-hardening]]
