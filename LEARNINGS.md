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

## 2026-07-17 — 002 Paragraphs as markdown: does it break TTS/timing?

**Believed**: Carrying trafilatura markdown to the render layer might break clean audio or exact
per-paragraph timing; a single markdown extraction with spoken text *derived* from it (display and
spoken sharing one segmentation and index) would keep alignment structural and need no TTS change.

**Observed**: It held. One markdown extraction split into units (boundary = blank line, since markdown
mode hard-wraps; lists split per-item; blockquotes/tables kept raw) yields `display[]`; a markdown-it-py
strip yields `spoken[]` (same index) that is fed to the *unchanged*, already-index-keyed TTS, whose
timeline zips back by index. On the real article: 55 aligned units, 0 residual markdown syntax, timing
contiguous with last `end` == duration (846 s), and user-confirmed clean natural audio. A raw-vs-clean
A/B confirmed the strip is load-bearing — Kokoro vocalizes syntax when fed raw markdown. The real risks
were segmentation and the strip (CommonMark-invalid run-in bold leaked `**`; word-boundary restoration
must be close-side-only), not the HTML→markdown boundary. A mandatory synthetic snippet caught a
blockquote `>` leak the blockquote-free real article couldn't.

**Learned**: For markdown read-along, make one extraction the source of truth and *derive* spoken text
from it, keyed by index — alignment becomes structural, not reconciled, and (because a paragraph-timing
TTS is naturally index-keyed) no TTS contract change is needed. The hard part isn't extraction fidelity;
it's segmentation (markdown hard-wraps) and a strip robust to a library's technically-invalid markdown.
When the real artifact can't exercise a load-bearing disproof condition, a small synthetic probe kept
separate from the real-artifact judgment is what makes that condition falsifiable.

**Scope**: Self-use, Nagara only, one clean-HTML article end-to-end plus a synthetic snippet. Inline/
heading/list proven end-to-end (audio + timing); blockquote/code/table proven strip-level only, and
tables further need `include_tables=True` (untested extraction toggle). Not evidence of generalization
across article types/formatting density, of demand, or of the player UX.

**Therefore**: Promote the whole markdown feature (all seven construct classes) to a new `PRODUCT.md`
milestone. Follow-ups to `BACKLOG.md`: end-to-end validation of blockquote/code/table on a
formatting-heavy fixture + `include_tables` decision; the right spoken form for code blocks; a
markdown-aware `_clean_paragraphs` at graduation. Process learning folded into the project's
`.zenku/experiment-start.md` extension.

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
