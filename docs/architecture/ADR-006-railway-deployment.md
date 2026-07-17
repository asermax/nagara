# ADR-006 — Railway production deployment (managed Postgres + object storage, serverless)

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md) (verdict routed production infra to the backlog as the graduation follow-up) **Related**: [ADR-002](ADR-002-api-key-as-identity.md), [ADR-003](ADR-003-sqlalchemy-sqlite-to-postgres.md), [DES-002](../design/DES-002-config-selected-backend.md)

## Context

The API must run somewhere reachable so the queue is usable by an agent client and future web surfaces. The product is demand-unproven, so idle cost matters more than steady-state throughput, and the operational surface should stay small. Persistence and audio storage both need managed homes (see ADR-003, DES-002).

## Decision

We deploy on **Railway** as a single project holding three resources: the **API service**, a **managed Postgres** database, and a **managed S3-compatible bucket** for audio. The API reaches Postgres over Railway's **private network**; the bucket is reached over its S3 endpoint with credentials supplied as service environment variables. The API service is built with Railway's default builder from the uv-managed project manifest (no bespoke build recipe) and is set to **serverless (scale-to-zero)**: it sleeps when idle and wakes on the next request. Database schema migrations are applied by a **pre-deploy step** before each new release serves traffic.

## Consequences

- **Near-zero idle cost** in exchange for a cold start on the first request after the service has slept. This suits a demand-validation MVP.
- Scale-to-zero shapes upstream choices: the Postgres engine holds no warm connection (per-request lifecycle, ADR-003), and schema migration runs as a pre-deploy step rather than on process start, so a wake is a container start, not a migration.
- **Secrets live in the service environment** (API key, database URL as a private-network reference, bucket credentials, TTS platform tokens); the deploy upload excludes the local virtualenv, database, and cached audio.
- **Single-project blast radius**: the API, its database, and its bucket share one project and environment; a second environment (staging) is a later addition, not part of this decision.
- Managed Postgres itself does not scale to zero; serverless applies to the API service only.
- **DNS and TLS**: the public endpoint is a custom domain whose DNS is managed in Cloudflare (DNS-only, not proxied — proxying blocks certificate validation), with TLS issued by Railway.

## Alternatives considered and not chosen

- **Another PaaS (Fly.io, Render)** — not chosen: Railway is the pre-declared target and provides first-party managed Postgres, S3-compatible buckets, and CLI provisioning in one place, with no reason to diverge.
- **An always-on VM or container** — not chosen: it forgoes scale-to-zero and pays steady idle cost for a product whose demand is unproven.
- **Self-hosted Postgres / self-hosted object storage** — not chosen: unwarranted operational burden versus the managed offerings for a single-service MVP.
