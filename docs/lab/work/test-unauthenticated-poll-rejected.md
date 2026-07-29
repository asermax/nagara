---
title: "Test that GET /items/{id} rejects a missing key"
tags:
  - work
summary: "The poll route has no direct test for a missing or incorrect X-API-Key, unlike the create and audio routes: the guard is shared, so this is a regression net, not a suspected bug."
status: open
kind: chore
priority: soon
size: small
---

# Test that GET /items/{id} rejects a missing key

## What

From the `enqueue-to-audio-api` spec's R8: "a request with a missing or incorrect credential to **any** route (enqueue, poll, or audio)... is rejected as unauthorized."

`test_post_requires_key` and `test_audio_requires_key` cover two of the three routes; there is no `test_get_requires_key` for `GET /items/{id}`. The guard (`require_key`) is wired once at the router level (`APIRouter(prefix="/items", dependencies=[Depends(require_key)])`, see [[authentication]]) and applies identically to all three routes, so this is very likely fine today. It is a `chore`, not a `defect`: nothing suggests the poll route behaves differently, but nothing pins that down either, and a future change to per-route dependencies would not be caught without this test.

---

Related: [[lab/README|the lab]] · [[authentication]]
