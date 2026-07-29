---
title: "Article list (queue)"
tags:
  - work
summary: "A view of the user's items with status (queued → generating → ready) and a link to each one's player."
status: open
kind: slice
priority: soon
size: medium
---

# Article list (queue)

## What

A view listing the current user's items with their status (`generating → ready`, or `failed`) and a link into each one's player: the queue itself, described from the user's side in [[queue|the queue]]. Depends on [[api-hardening]]'s `GET /items` list endpoint.

Second of six in the build order agreed 2026-07-17, dogfood cluster (single-user, no login yet).

---

Related: [[lab/README|the lab]] · [[queue]] · [[api-hardening]]
