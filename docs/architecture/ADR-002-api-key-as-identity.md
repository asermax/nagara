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
- **Uniform protection**: no route is public, including audio — a private item's audio is never reachable without the key.
- **Browser audio is a known gap.** A browser `<audio>` element cannot attach a custom header, so it cannot fetch key-protected audio directly. Serving audio to an in-browser player will need signed URLs or cookie/session auth — a graduation task, tracked in the backlog, not solved here.
- **Multi-user is a real replacement, not an extension.** Going multi-user means introducing genuine identity and per-user key management, replacing the single-key shim rather than adding to it.

## Alternatives considered and not chosen

- **OAuth / multi-user identity now** — deferred: there is no audience to onboard yet, and it is a whole slice of its own; building it now would be speculative.
- **No authentication** — unacceptable: items are private by definition.
- **A separate identity layer over the key** — unnecessary at single-user scale; the key doubling as identity is the simplest thing that keeps items private.
