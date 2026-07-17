# Roadmap

Per-milestone build order for the product half. Each milestone in `PRODUCT.md` that is being built
gets a section here. Order and the dependency graph are decided in `/roadmap`; features then flow
through `/spec → /design → /implement → /reconcile`.

## Milestone 1 — Enqueue-to-audio API (the backend spine)

Source: [`PRODUCT.md` Milestone 1](../../PRODUCT.md). The milestone is a single coherent feature —
the API that turns a public article URL into a private, player-ready read-along audio item — built in
place under the spike-at-root / graduate-in-place convention and documented after the fact.

### Features

| Feature | Depends on | Parallel-safe with | Source evidence | Status |
|---------|-----------|--------------------|-----------------|--------|
| [`enqueue-to-audio-api`](../feature-specs/enqueue-to-audio-api.md) | — | — | [exp 001](../../experiments/001-player-ready-item/README.md) | ✓ Reconciled |

Status values: `✗ Defined` → `⧗ Spec` → `✓ Spec` → `⧗ Design` → `✓ Design` → `⧗ Implemented` → `✓ Implemented` → `✓ Reconciled`.

### Dependency graph

```mermaid
graph TD
  A[enqueue-to-audio-api]
```

### Build order

1. `enqueue-to-audio-api` — the whole milestone; no dependencies. It is the spine every future
   surface (read-along player, queue list, settings) and the public-funnel slices consume.

---

## Milestone 2 — Markdown-formatted read-along content

Source: [`PRODUCT.md` Milestone 2](../../PRODUCT.md). The milestone is a single coherent feature —
paragraphs carry markdown for display while the spoken audio stays clean, aligned by index to the
unchanged TTS timeline. It evolves the extraction and item contract the backend spine already ships.

### Features

| Feature | Depends on | Parallel-safe with | Source evidence | Status |
|---------|-----------|--------------------|-----------------|--------|
| [`markdown-read-along-content`](../feature-specs/markdown-read-along-content.md) | `enqueue-to-audio-api` | — | [exp 002](../../experiments/002-markdown-paragraphs/README.md) | ✓ Reconciled |

Status values: `✗ Defined` → `⧗ Spec` → `✓ Spec` → `⧗ Design` → `✓ Design` → `⧗ Implemented` → `✓ Implemented` → `✓ Reconciled`.

### Dependency graph

```mermaid
graph TD
  A[enqueue-to-audio-api] --> B[markdown-read-along-content]
```

### Build order

1. `markdown-read-along-content` — the whole milestone. Depends on the backend spine
   (`enqueue-to-audio-api`), whose extraction step and item/read-along contract it evolves: display
   paragraphs carry markdown, spoken text is derived and fed to the unchanged TTS, and the timeline
   zips back by index.

---

*Future milestones append their own sections here as they are promoted from `PRODUCT.md` and become
worth building. The next candidates — the read-along player and the surfaces that consume this API —
are still in the experiment backlog (`BACKLOG.md`), not yet promoted.*
