---
title: "Article list (queue)"
tags:
  - quest
summary: "A view of the user's items with status (queued → generating → ready) and a link to each one's player."
status: open
type: build
adventure:
blocked_by:
  - api-hardening
priority: 2-soon
created: "2026-07-17"
---

# Article list (queue)

## What

A view listing the current user's items with their status (`generating → ready`, or `failed`) and a link into each one's player: the queue itself, described from the user's side in [[queue|the queue]]. Depends on [[api-hardening]]'s `GET /items` list endpoint.

Second of six in the build order agreed 2026-07-17, dogfood cluster (single-user, no login yet).

---

Related: [[quest-log/README|the quest log]] · [[queue]] · [[api-hardening]]
