---
title: "Test that GET /items/{id} rejects a missing key"
tags:
  - quest
summary: "The poll route has no direct test for a missing or incorrect X-API-Key, unlike the create and audio routes: the guard is shared, so this is a regression net, not a suspected bug."
status: open
type: build
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Test that GET /items/{id} rejects a missing key

## What

From the `enqueue-to-audio-api` spec's R8: "a request with a missing or incorrect credential to **any** route (enqueue, poll, or audio)... is rejected as unauthorized."

`test_post_requires_key` and `test_audio_requires_key` cover two of the three routes; there is no `test_get_requires_key` for `GET /items/{id}`. The guard (`require_key`) is wired once at the router level (`APIRouter(prefix="/items", dependencies=[Depends(require_key)])`, see [[authentication]]) and applies identically to all three routes, so this is very likely fine today. Nothing suggests the poll route behaves differently, but nothing pins that down either, and a future change to per-route dependencies would not be caught without this test.

---

Related: [[quest-log/README|the quest log]] · [[authentication]]
