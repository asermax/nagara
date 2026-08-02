---
title: "API hardening"
tags:
  - quest
summary: "Quota enforcement, a GET /items list endpoint, and API-key create/revoke: the furniture deferred out of the backend spine's promotion."
status: open
type: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# API hardening

## What

Furniture deliberately deferred out of [[audio-read-later-queue]]'s promotion, not yet built (the spine itself is in place, see that quest's answer): per-user quota enforcement (item-count tiers), a `GET /items` list endpoint, and API-key create/revoke (which also surfaces in the settings slice).

First of six in the build order agreed 2026-07-17, and the first of the **dogfood cluster** (single-user, no login yet), which is the spine everything else in that cluster consumes. The other cluster, public-funnel (auth, article creation, landing), turns the product into something a stranger can try, in service of [[validate-demand]].

---

Related: [[quest-log/README|the quest log]] · [[audio-read-later-queue]] · [[validate-demand]]
