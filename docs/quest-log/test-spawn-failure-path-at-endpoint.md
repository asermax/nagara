---
title: "Test the spawn-failure path at the endpoint"
tags:
  - quest
summary: "spawn_synthesis raising inside create_item has no covering test at the endpoint level: the code mirrors the already-tested extraction-failure branch, but nothing pins it down."
status: open
type: build
adventure:
blocked_by: []
priority: 2-soon
created: "2026-07-17"
---

# Test the spawn-failure path at the endpoint

## What

From the `enqueue-to-audio-api` spec's R4: "a URL that cannot be turned into audio at enqueue (not fetchable, fetchable but not HTML, or **synthesis cannot be dispatched**), When it is enqueued, Then the enqueue response itself is the item already in `failed`."

`api/app/endpoints/items.py::create_item` wraps `spawn_synthesis(...)` in a `try`/`except Exception` that sets `item.status = FAILED` and `item.error = f"spawn: {type(e).__name__}: {e}"` before falling through to `return item`: structurally identical to the extraction-failure branch just above it, which `test_post_extraction_failure_lands_failed` already covers. No test patches `spawn_synthesis` to raise and checks the resulting item.

This is a regression net, not a suspected defect: read against the code, the branch is a straightforward mirror of its tested sibling and there is no reason to think it is wrong. What is missing is the test, not a fix.

---

Related: [[quest-log/README|the quest log]]
