# Docs

Durable engineering docs — the product half of zenku. These describe the **current** system (what it
does and deliberately does not do), and are fed from the experiments that justified them.

- **`planning/ROADMAP.md`** — per-milestone feature ordering + dependency graph.
- **`feature-specs/`** — long-lived feature specs (*what* is guaranteed). Indexed by its `README.md`.
- **`feature-designs/`** — long-lived feature designs (*approach and mechanism*). Indexed by its `README.md`.
- **`architecture/`** — ADRs: one-time, hard-to-reverse, project-wide choices. Indexed by its `README.md`.
- **`design/`** — DES: repeatable cross-cutting patterns (used 2+ places). Indexed by its `README.md`.

**Milestone 1 — the backend spine** is documented here (built in place via
[experiment 001](../experiments/001-player-ready-item/README.md), graduate-in-place):

- Feature: [`feature-specs/enqueue-to-audio-api.md`](feature-specs/enqueue-to-audio-api.md) ·
  [`feature-designs/enqueue-to-audio-api.md`](feature-designs/enqueue-to-audio-api.md)
- Decisions: [ADR-001](architecture/ADR-001-modal-tts-zero-broker-async.md) (Modal zero-broker async) ·
  [ADR-002](architecture/ADR-002-api-key-as-identity.md) (API-key-as-identity) ·
  [ADR-003](architecture/ADR-003-sqlalchemy-sqlite-to-postgres.md) (SQLAlchemy SQLite→Postgres) ·
  [ADR-004](architecture/ADR-004-trafilatura-extraction-headless-deferred.md) (trafilatura extraction) ·
  [ADR-005](architecture/ADR-005-python-toolchain.md) (Python toolchain) ·
  [DES-001](design/DES-001-read-along-timing-windows.md) (read-along timing windows)

Feature ordering is in [`planning/ROADMAP.md`](planning/ROADMAP.md) — Milestone 1 is a single
feature (the backend spine), already `✓ Reconciled`. These docs were back-filled from the built code
rather than authored ahead of it.
