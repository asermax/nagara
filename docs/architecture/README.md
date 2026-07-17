# Architecture Decisions (ADR index)

One-time, hard-to-reverse, project-wide choices. Repeatable patterns live in the
[DES index](../design/README.md).

| ID | Decision | Status | Grounded in |
|----|----------|--------|-------------|
| [ADR-001](ADR-001-modal-tts-zero-broker-async.md) | Modal-hosted TTS as a separate deployable with zero-broker async | Accepted | [exp 001](../../experiments/001-player-ready-item/README.md) |
| [ADR-002](ADR-002-api-key-as-identity.md) | API-key-as-identity auth (single-user, OAuth deferred) | Accepted | [exp 001](../../experiments/001-player-ready-item/README.md) |
| [ADR-003](ADR-003-sqlalchemy-sqlite-to-postgres.md) | SQLAlchemy ORM: SQLite locally, Postgres in production (Alembic migrations) | Accepted | [exp 001](../../experiments/001-player-ready-item/README.md) |
| [ADR-004](ADR-004-trafilatura-extraction-headless-deferred.md) | Server-side extraction with trafilatura; headless deferred | Accepted | [exp 001](../../experiments/001-player-ready-item/README.md) |
| [ADR-005](ADR-005-python-toolchain.md) | Python toolchain: uv, ruff, ty, pytest | Accepted | — |
| [ADR-006](ADR-006-railway-deployment.md) | Railway production deployment: managed Postgres + object storage, serverless | Accepted | [exp 001](../../experiments/001-player-ready-item/README.md) |
