# Experiments

Each experiment answers **one** question, pre-registered *before* it runs and judged against real
work. An experiment is a folder `NNN-slug/` with a `README.md` one-pager. Numbers are monotonic and
never reused; **nothing here is ever deleted** — a documented dead end is a deliverable.

Flow: `/experiment-start` (pre-register the one-pager) → `/experiment-run` (shape + build + run the
judging sessions) → `/experiment-conclude` (forced verdict → `LEARNINGS.md`, promote →
`PRODUCT.md`).

Spikes are **built at root** (`web/`, `api/`) and hardened in place — see the Spike location note in
`CLAUDE.md`. A one-pager points at the root code it exercises rather than owning an isolated sandbox.

## One-pager template

```markdown
# NNN — <title>

**Question**: the single question this answers. If it needs an "and", split it — one question per
experiment; the rest go back to `BACKLOG.md`. **Hypothesis**: what you expect to see, stated so it
can be proven wrong. **Judging**: how you'll know the answer — decided *before* running. Two lenses,
because either alone has documented failure modes:
- a **task** criterion — something concrete and checkable to do against the real work artifact (a
  diff/PR, a dataset, a document, a task outcome — whatever this project produces);
- an **insight** criterion — what understanding the experiment should produce. Include the **kill
  criterion / timebox**: a few focused sessions; if it needs more, that itself is a finding.

## Setup

What gets built, fed with what data, judged against which real task. Includes the **session
protocol**: the 2–3 scorable tasks to run against the real work artifact, interleaved with
open-ended "what do I understand now that I didn't?" blocks. Written/refined collaboratively in
`/experiment-run` and validated by `zenku:shape-reviewer`.

**Spike location**: where this experiment's sandbox code lives (per the project's `## zenku`
conventions, or chosen and recorded here).

## Notes

The insight log, appended live while running: dated discoveries the experiment produced, and
expected insights that did *not* materialize. The verdict is judged against this record, not memory.

## Verdict

The answer + the decision it led to — **promote / drop / follow-up** — with its scope stated
explicitly. Self-use on one's own project is not evidence a result generalizes beyond that.
```

## Index

| # | Experiment | Verdict |
|---|------------|---------|
| [001](001-player-ready-item/README.md) | Slice 1: does a real push yield a player-ready item? | ✅ Promote — enqueue→player-ready pipeline proven (→ PRODUCT M1) |
| [002](002-markdown-paragraphs/README.md) | Paragraphs as markdown: does it break TTS/timing? | ✅ Promote — single-extraction + index-keyed strip carries markdown, no TTS change (→ PRODUCT M2) |
