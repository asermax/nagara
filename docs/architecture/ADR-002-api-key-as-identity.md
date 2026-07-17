# ADR-002 — API-key-as-identity authentication (single-user, OAuth deferred)

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 001](../../experiments/001-player-ready-item/README.md)

## Context

Items are private — an article someone enqueues is theirs, not public. Every route that reads or creates an item must therefore be authenticated. Two forces shape the auth model right now:

- **The first consumer is an agent, not a browser.** The dogfood client (Tachikoma) pushes URLs machine-to-machine; it wants to present one credential on each call, not run an interactive login dance.
- **There is no audience yet.** Multi-user onboarding and OAuth are a later slice, built in service of the demand question — not needed to make the private queue work for its first user.

## Decision

We authenticate with a **single API key that acts as the user identity.** The key is presented on an API-key header, and it guards **every** route — item creation, item polling, and audio delivery alike. Possessing the key *is* being the user; there is no separate identity, session, or login. OAuth and multi-user identity are deferred to a later slice.

## Consequences

- **Trivial for an agent client**: one header on every call, no token exchange or refresh.
- **Every item route is guarded**: item creation, polling, and the audio route all require the key; a private item is never reachable without it. The one public route is an unauthenticated `/health` liveness endpoint, which exposes no item data — a deliberate, narrow exception for platform health checks.
- **Audio reaches a headerless browser via a short-lived link.** The audio route requires the key to *obtain* a link and only mints one for a `ready` item; in production it returns a redirect to a short-lived presigned object-storage URL that a browser `<audio>` element can fetch without a custom header. The store itself stays private — access is only via links minted to authenticated callers, and those links expire. (The web player's client-side integration — fetching the link with the key, then feeding the element — remains its own slice.)
- **Multi-user is a real replacement, not an extension.** Going multi-user means introducing genuine identity and per-user key management, replacing the single-key shim rather than adding to it.

## Alternatives considered and not chosen

- **OAuth / multi-user identity now** — deferred: there is no audience to onboard yet, and it is a whole slice of its own; building it now would be speculative.
- **No authentication** — unacceptable: items are private by definition.
- **A separate identity layer over the key** — unnecessary at single-user scale; the key doubling as identity is the simplest thing that keeps items private.
