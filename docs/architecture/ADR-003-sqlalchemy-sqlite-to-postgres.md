# ADR-003 — SQLAlchemy ORM: SQLite locally, Postgres in production

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md) **Related**: [ADR-006](ADR-006-railway-deployment.md), [DES-002](../design/DES-002-config-selected-backend.md)

## Context

The queue needs durable per-item state: the URL, title, status, voice, the read-along timing, any error, and the handle to the in-flight synthesis call. Production runs on Railway + Postgres; local development and tests run on a zero-setup embedded store. The persistence layer must serve both backends without being rewritten for either.

## Decision

We persist through the **SQLAlchemy ORM**. The backing store is chosen by connection string — **Postgres in production, SQLite locally and in tests** — so the store changes with an engine swap rather than a persistence rewrite (an instance of the config-selected backend pattern, [DES-002](../design/DES-002-config-selected-backend.md)). Timing data (the per-paragraph windows) is stored in a JSON-typed column, which both stores support.

The **schema is managed by Alembic migrations** for the databases that must persist and evolve — local dev and production — applied before the app serves. The test database is disposable and rebuilt per run directly from the models.

## Consequences

- **The store swaps by connection string**: the models and query code are unaffected by which backend is in use.
- The embedded store requires a **cross-thread connection setting** because the API serves blocking DB work from a threadpool; this is a store-specific accommodation, not a design constraint on the model.
- The Postgres engine **opens and closes a connection per request** (no pooling) so an idle service holds no warm connection and can scale to zero (serverless — [ADR-006](ADR-006-railway-deployment.md)).
- **Schema changes are versioned migrations.** Alembic owns the dev/prod schema; a schema change means a new migration, applied before the new release serves. Tests build their throwaway schema directly from the models, so the migration path is not exercised by the suite — an autogenerate check guards that the migrations still match the models.
- Audio itself is **not** stored in the database — it lives in object storage in production and in local files in development (see [DES-002](../design/DES-002-config-selected-backend.md) and the feature design); the database holds only metadata and the timing JSON.

## Alternatives considered and not chosen

- **A raw embedded-DB driver (no ORM)** — not chosen: it would tie the persistence code to the embedded store's SQL dialect and force a rewrite to reach Postgres.
- **Postgres everywhere, including local/tests** — not chosen: an embedded store keeps the local loop and the test suite zero-setup and fast, and the ORM seam makes the production swap cheap.
- **Schema created from the models everywhere (no migration tooling)** — not chosen for the real databases: it cannot evolve a schema against already-persisted production data. Retained only for the disposable test database.
