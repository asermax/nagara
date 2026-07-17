# DES-002 — Config-selected backend

**Status**: Active **Applies to**: persistence (the database engine) and audio storage — the two seams that differ between local development and production **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md) (graduation to production), [ADR-003](../architecture/ADR-003-sqlalchemy-sqlite-to-postgres.md)

## Pattern

Where a capability has a local-development implementation and a different production implementation, select the implementation **once, at startup, from configuration** — never from an environment name or a test flag in the runtime code.

- Each backend hides behind a small interface; concrete implementations sit behind it.
- A single factory reads configuration and returns the appropriate implementation. The rest of the code depends only on the interface.
- "Which backend" is expressed as configuration a deployment supplies (a connection string, a set of credentials), not as `if production` / `if testing` branches.

Two instances:

- **Database engine** — the SQLAlchemy engine is built from the connection string: Postgres when one is supplied, the embedded SQLite store otherwise ([ADR-003](../architecture/ADR-003-sqlalchemy-sqlite-to-postgres.md)).
- **Audio storage** — an audio-storage interface with a local-file implementation and an object-storage implementation; the factory picks the object store when its credentials are configured, and the local files otherwise.

## Rationale

- **Dev/prod code parity.** The same code runs in every environment; only the supplied configuration differs. There is no environment-specific branch to drift, and no production path that tests never exercise because a flag hid it.
- **Cheap graduation.** Moving a capability from its local stand-in to its managed production home is a new implementation behind the existing interface plus configuration — not a rewrite of the callers.
- **Honest fallback.** Absent or partial production configuration falls back to the local implementation rather than failing obscurely, so a misconfiguration is visible as "it used the local backend", not a crash deep in a request.

## Consequences

- Each new cross-environment capability adds an interface + a factory rather than a conditional at each call site.
- Configuration completeness matters: a half-supplied credential set must be treated as "not configured" so the fallback is deliberate, not accidental.
