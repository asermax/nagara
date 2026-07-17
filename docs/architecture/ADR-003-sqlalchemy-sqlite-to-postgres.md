# ADR-003 — SQLAlchemy ORM over SQLite now, Postgres at graduation

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md)

## Context

The queue needs durable per-item state: the URL, title, status, voice, the read-along timing, any error, and the handle to the in-flight synthesis call. The production target is Railway + Postgres, but the current single-user spike runs locally, where a zero-setup embedded store is enough. The choice must let storage graduate from the local store to Postgres **without rewriting the persistence layer**.

## Decision

We persist through the **SQLAlchemy ORM**, with **SQLite as the current backing store and Postgres as the graduation target.** The ORM is chosen precisely as the seam that lets the backing store change with a connection-string/engine swap rather than a persistence rewrite. Timing data (the per-paragraph windows) is stored in a JSON-typed column, which both stores support.

## Consequences

- **Graduation is a narrow change**: point the engine at Postgres instead of the local file; the models and query code are unaffected.
- The embedded store requires a **cross-thread connection setting** because the API serves blocking DB work from a threadpool; this is a store-specific accommodation, not a design constraint on the model.
- **No migration tooling yet.** The schema is created directly from the models. A real migration story (e.g. Alembic) is a graduation concern, needed once the schema must evolve against persisted Postgres data.
- Audio itself is **not** stored in the database — see the feature design's decision to keep audio as files on disk; the database holds only metadata and the timing JSON.

## Alternatives considered and not chosen

- **A raw embedded-DB driver (no ORM)** — not chosen: it would tie the persistence code to the embedded store's SQL dialect and force a rewrite to reach Postgres.
- **Postgres from day one** — deferred: it is unwarranted infrastructure for a single-user local spike; the ORM seam means adopting it later costs little.
