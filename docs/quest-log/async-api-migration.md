---
title: "Async API migration"
tags:
  - quest
summary: "Every endpoint and the database session go async, with trafilatura, boto3 and Modal bridged through a threadpool, so enrichment can fan out later."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 2-soon
created: "2026-08-02"
---

# Async API migration

## What

Nothing observable changes. Every route behaves exactly as it did, on an async stack.

This is a prerequisite rather than a feature. [[richer-extraction]] needs to issue an article's image fetches and describe calls concurrently, because the five-minute ceiling on a `queued` item is only defensible if it does. Serialized, the corpus's code-heavy article takes 309 seconds and poll starts failing items that are working correctly.

Choosing `asyncio.gather` over a thread pool forces this decision rather than dodging it: async endpoints over a sync session would relocate the impedance mismatch from the enrichment handler onto every endpoint, which is what going async was meant to avoid.

Doing it here, before [[queued-item-lifecycle]] rewrites the same endpoints, avoids paying for the rewrite twice.

## Design

### What changes

`async def` endpoints, `create_async_engine` and `AsyncSession` behind the existing configuration-driven factory. Invariant 6 holds: the session is chosen by configuration, never by an environment name.

### Three sync libraries that cannot be awaited

Each is load-bearing and blocking, and each stalls the single event loop for every request if it is called directly from an `async def`. All three go through `run_in_threadpool` or `asyncio.to_thread`:

| Library | Call | Why it blocks |
|---|---|---|
| trafilatura | `fetch_response`, `extract` | a network fetch plus a CPU-bound extract |
| boto3 | `BucketAudioStorage.store` | synchronous S3 client |
| Modal client | `spawn_synthesis`, `poll_synthesis` | synchronous remote call |

Native async applies only where the library is genuinely async, which later means the describer's `google-genai` async client and image fetches through `httpx.AsyncClient`.

### What this does not change

Invariant 5 is untouched by this quest. No broker, no worker process, no sweeper. The clause about work outliving the response belongs to [[queued-item-lifecycle]], which is what introduces it.

The Modal carve-out in the test suite stands: `spawn_synthesis` and `poll_synthesis` stay module-patched, because the Modal client is not plain HTTP that vcrpy replays cleanly.

### How it is verified

The existing suite is the test. Every current test in `test_main.py` passes unchanged against async endpoints, driven by `TestClient`, which handles an async app transparently. A test that needed rewriting to accommodate the migration is a signal the migration changed behaviour it should not have.

## Answer

Built. The API runs on async SQLAlchemy end to end: `create_async_engine` with `NullPool`, `async_sessionmaker`, and a `get_db` dependency that commits on success and rolls back on error. The sync libraries that remain — trafilatura, the Modal client, boto3 — are each bridged with `run_in_threadpool` at their call site rather than being replaced.

**How far it reaches.** The database URL stays the logical sync-dialect one and is mapped onto the matching async driver at runtime (`asyncpg` for Postgres, `aiosqlite` for SQLite), because Alembic drives psycopg2 from the same setting. Both drivers are therefore load-bearing and neither is dead weight.

**What would make it stop being true.** A new sync library called from a route without the threadpool bridge — it blocks the event loop and nothing in the suite catches it, because a blocked loop still returns correct answers.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[queued-item-lifecycle]] · [[persistence-and-storage]]
