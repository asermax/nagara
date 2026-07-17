# Learnings

Append-only. One entry per concluded experiment, newest at the top. Each entry is grounded in its
experiment's insight log (`experiments/NNN-slug/README.md` → `## Notes`), never in memory.

Entry shape:

```markdown
## YYYY-MM-DD — NNN <title>

**Believed**: the hypothesis going in. **Observed**: what actually happened, grounded in the insight
log. **Learned**: the insight, stated so it generalizes. **Scope**: how far the evidence actually
reaches (e.g. self-use, on this project only). **Therefore**: the decision — what changes from here
(promote / drop / follow-up).
```

---

## 2026-07-17 — 001 Slice 1: does a real push yield a player-ready item?

**Believed**: The `enqueue(url) → eager-generate → pollable item` shape would produce player-ready
items, but URL→clean-paragraph extraction was the sleeper risk, and JS-rendered pages were expected to
need a headless browser.

**Observed**: All four HTML fixtures (clean blog, magazine longread, newsletter, JS-rendered Substack)
fetched and extracted into trustworthy paragraph splits with plain `trafilatura` — no headless browser
needed; the Substack server-renders its post. The PDF cleanly failed on a content-type check.
Per-paragraph timing (the inter-paragraph pause folded into the preceding window) reconciled exactly
with audio duration. Zero-broker Modal `spawn()` + lazy `FunctionCall.get(timeout=0)` cleanly told a
running job (`generating`) from a crashed one (`failed`+`error`). Split quality validated good; audio
"fantastic".

**Learned**: A thin FastAPI + `trafilatura` + Modal-Kokoro pipeline turns a public article URL into a
player-ready read-along item (Opus audio + per-paragraph timing), and worked cleanly across the tested
public-HTML types.
Server-side extraction is good enough well past where a headless browser seemed necessary — reach for
headless only when a specific site actually fails, not preemptively. Modal's own invocation primitives
are a sufficient async layer at this scale; a separate task queue is unwarranted.

**Scope**: Self-use, Nagara only, one session, 5 real articles from the owner's reading list,
single-user spike. Not evidence of demand, of generalization beyond these sites/types, or of
multi-user behavior.

**Therefore**: Promote the pipeline (API shape + extraction + TTS/read-along contract) to `PRODUCT.md`
Milestone 1 as the backend spine. Defer prose-boilerplate stripping, multi-user + auth-for-audio,
Postgres/Railway, and API furniture (quota, list, key CRUD) to `BACKLOG.md`. Headless-browser fetch is
deprioritized — not needed yet.
