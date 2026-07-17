# ADR-001 — Modal-hosted TTS as a separate deployable with zero-broker async

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md)

## Context

Turning an article into audio requires GPU-backed text-to-speech (Kokoro-82M). Two forces shape how that compute is wired in:

- **The TTS code is an image definition, not a callable library.** The synthesis code *is* the specification of the container image that runs on the GPU host — it declares its own base image, system packages, and model bake step, and is uploaded as a unit. It therefore cannot execute inside the API process; it must be a separately deployed service the API invokes remotely.
- **Synthesis is slow relative to a request.** A full article takes seconds to minutes to render. An enqueue call cannot hold a connection open until audio is ready, so generation must run asynchronously and its result be retrieved later.

The open question was what provides the async layer: a conventional broker + worker stack (a task queue with a message broker and a separate worker process), or the compute platform's own invocation primitives.

## Decision

We run TTS as a **separate Modal app** with its own deploy lifecycle, and use **Modal's own invocation primitives as the async layer — no broker, no worker process, no queue infrastructure.**

- The API **spawns** a remote call on the deployed TTS function and persists the returned call handle on the item. The enqueue request then returns immediately.
- The result is resolved **lazily**: when a client polls, the API fetches that call's result with a non-blocking read. The read's outcome carries the job state directly — a *still-running* call surfaces as a timeout (the item stays generating), and a *crashed* call **re-raises the remote exception** across the boundary (the item becomes failed with that error recorded).

The API stores only the call handle and the eventual result; it runs no worker, no scheduler, and no message broker.

## Consequences

- **No broker infrastructure** to deploy, scale, secure, or monitor — a significant operational saving at this scale.
- **Crash semantics come for free**: the running-vs-failed distinction is a property of the result read (timeout vs. re-raised remote exception), not something we build or track separately.
- The two deployables graduate independently: the TTS service ships on its own `deploy` cadence, decoupled from the API.
- **Clients must poll** — the API cannot push completion. This is the async-and-poll interaction the feature spec commits to; a client observes `generating` until a poll transitions the item to `ready`/`failed`.
- The execution substrate is now **coupled to Modal**. Moving off it means replacing both the compute host and the async layer together.
- Cold start is bounded to a few seconds via GPU + memory snapshotting; a warm container is kept briefly to absorb a session's burst of pushes.

## Alternatives considered and not chosen

- **A broker + worker queue (e.g. Celery/RQ with Redis)** — not chosen: it adds a broker and a worker process to run and monitor for no benefit the platform's own primitives don't already provide, and it would still need the same crash/running bookkeeping we now get from the result read.
- **TTS inside the API process** — not possible: the synthesis code is an image definition uploaded to the GPU platform, not an importable in-process library.
- **A synchronous block-until-ready enqueue** — not chosen: it would hold a connection for minutes and push timeout/retry tuning onto every client; eager-generate-then-poll keeps enqueue instant.
