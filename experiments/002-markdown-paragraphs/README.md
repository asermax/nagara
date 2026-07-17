# 002 — Paragraphs as markdown: does it break TTS/timing?

**Question**: Can a paragraph carry trafilatura's markdown output to the render layer while keeping
Kokoro's audio **clean** (no vocalized syntax) and its per-paragraph **timing exact and contiguous**
— i.e. can the display-markdown and the spoken/timed audio be kept referring to the same units without
a reconciliation step? This is a pipeline-**integrity** question; whether the formatting is faithfully
extracted, and whether it's ultimately *worth* the added complexity, are treated as givens here and
parked as follow-ups (see `BACKLOG.md`). **Testable scope this run**: inline emphasis, links,
headings, and lists are carried **end-to-end** (extraction → strip → TTS → audio + timing) against the
real article; **code blocks and blockquotes are strip-level only** (unit-checked against a synthetic
snippet — their timing + audio round-trip stays untested until a formatting-heavy fixture); **tables
are out of scope** (`include_tables=False`, matching today's pipeline).

**Hypothesis**: A **single** markdown extraction can be the one source of truth, with spoken text
*derived* from it — so display and audio share one segmentation and one index, and alignment is
structural rather than reconciled. Concretely: `trafilatura.extract(output_format="markdown",
include_formatting, include_links, include_tables=False)` yields `display[]`; a small markdown→plain
renderer produces `spoken[]` (same length, same index, syntax stripped, links reduced to their anchor
text); `spoken[]` goes to the **existing, unchanged** TTS service, which already returns timing keyed
by list position; the API zips that timing onto both arrays by index. Audio reads as natural prose,
timing invariants hold, and no TTS/Modal contract change is needed. It is **disproven** if any of:

1. **Strip isn't general** — `spoken[]` can't be made syntax-free (residual `* _ # [ ] (url) `` > |`)
   or links leak their URL, without per-article/per-construct special-casing beyond a small general
   renderer;
2. **Alignment-free promise fails** — some construct forces a split/merge that breaks the 1:1 between
   `display[i]`, `spoken[i]`, and the timeline (i.e. the single-segmentation claim doesn't hold);
3. **Timing breaks** — the timeline over the markdown-derived `spoken[]` is non-monotonic,
   overlapping, or its last `end` no longer ≈ audio `duration` (the 001 invariants regress);
4. **Audio dirties** — playback vocalizes markdown syntax or reads unnaturally;
5. **Code blocks fragment** — a fenced code block (if the fixture contains one) shatters into
   per-line degenerate mini-"paragraphs" that can't be re-merged into one atomic unit cleanly.

**Judging** — judged against the real work artifact: the `display[]` markdown + derived `spoken[]` +
index-keyed timeline + generated audio, produced for **one real reading-list article** (Mitchell
Hashimoto, *My AI Adoption Journey* — the clean-HTML case from 001), snapshotted into the sandbox.

- **Task criteria** (concrete, checkable against the artifact):
  1. **Clean spoken text** — every `spoken[i]` is free of markdown syntax (`* _ # [ ] (url) `` > |`)
     and each link is reduced to its anchor text with the URL dropped. Checkable across the array.
  2. **Structural alignment** — `len(display) == len(spoken) == len(timeline)`, and index `i` refers
     to the same logical unit in all three; zip-by-index yields a coherent per-unit
     `{display, spoken, start, end}`. (The core of "does it break timing": under the single-extraction
     model this must hold *by construction*, so on the clean fixture it will almost certainly pass
     without stress — a failure means the model is wrong. Its real refutation power lives in the
     hostile-construct path, which is why the synthetic code-block/blockquote check below is mandatory,
     not optional.)
  3. **Timing invariants** — the returned timeline is monotonic, non-overlapping, contiguous, with the
     last `end` ≈ audio `duration` (the 001 checks), on the markdown-derived `spoken[]`.
  4. **Clean audio** — on listen, no markdown syntax is spoken; it reads as natural prose (the
     load-bearing perceptual check).
  5. **Code-block / blockquote handling (strip-level)** — against the mandatory synthetic snippet, a
     fenced code block is merged into one atomic unit (not fragmented into per-line windows) and a
     blockquote strips to clean spoken prose. This is a **strip-level** check only; the timing + audio
     round-trip for these constructs is **not** tested this run (no fixture exercises them end-to-end)
     and is recorded as deferred, never claimed.
- **Insight criterion**: Does the single-extraction + index-keyed-join model actually make alignment
  *structural* end-to-end, or does some construct still force display and audio apart? Where is the
  boundary between markdown that carries cleanly into a read-along (inline emphasis, links, headings,
  lists) and markdown that fights it (code blocks' embedded newlines)? And — honestly — did the clean
  fixture even *contain* the hazardous constructs, or does the real risk remain deferred to a
  formatting-heavy article? (Tables are consciously out of scope this run — `include_tables=False` —
  and their unspeakability routes to the deferred formatting-heavy follow-up.)
- **Kill / timebox**: ≤ 2 focused sessions. The sandbox is small (one script, one fixture, the TTS
  service reused as-is), so this is far cheaper than 001. **Kill branch**: if even on clean HTML the
  strip needs per-article special-casing, or alignment can't be kept structural, the finding is that
  markdown-in-the-contract needs a dedicated normalization layer — record that and **keep plain text**
  (don't adopt markdown yet). **Expected verdict scope even on success**: timing + audio integrity is
  established for inline + link + heading + list markdown (carried end-to-end against the real article);
  code-block/blockquote handling is verified only at the strip level (synthetic snippet), and their
  timing + audio round-trip, plus tables, are deferred to a follow-up with a formatting-heavy fixture.

## Setup

**Mechanism is left to discovery; the judgment above is fixed.** Research (2026-07-17) ranked three
candidate shapes and pre-killed one:

- **(a) Dual extraction** (plain pass for audio + markdown pass for display, then reconcile) — **dead
  before spiking.** trafilatura's segmentation is *tree-driven*, and `include_tables`/`include_links`
  are tree-shape decisions, not rendering decorations — so two independent passes provably diverge
  whenever an article has a table, manufacturing the exact alignment risk this experiment exists to
  avoid.
- **(b) Single markdown extraction, text-keyed timing** — dominated: re-derives a text-matching join
  that the TTS service doesn't need.
- **(c) Single markdown extraction, index-keyed timing** — **recommended and pre-registered as the
  hypothesis.** The TTS service already returns timing by list position (`{index, start, end}`), so
  this needs **no TTS/Modal contract change**; alignment is structural because there is one
  segmentation.

**What gets built** (the cheapest thing that answers the question; everything the judging doesn't test
is hardcoded — one voice, one fixture, no DB, no API server):

- **One-time fixture snapshot** — fetch the article's raw HTML and store it under the sandbox's
  `fixtures/` so every run is offline and repeatable (the 001 HTML snapshots weren't kept).
- **Markdown extraction + unit split** — trafilatura in markdown mode (`include_formatting`,
  `include_links`, `include_tables=False`) → one markdown string, then split into `display[]` units.
  **Unit boundary = blank line, not `\n`** (task 1: markdown mode hard-wraps paragraphs across single
  `\n`); within a paragraph block, soft-wraps are joined; a **list block is split into per-item units**;
  a **fenced code block is kept as one atomic unit** *before* any splitting (trafilatura preserves its
  internal newlines and there is no upstream off-switch).
- **Spoken-text strip** — a small custom markdown→plain renderer built on **markdown-it-py** (no
  surveyed third-party plain-text package cleared the maintenance bar), run per unit: emphasis →
  inner text, link → anchor text (URL dropped), heading/list markers dropped. Must **restore the word
  boundary at emphasis/text adjacencies** (task 1: trafilatura drops the space in `**phrase**word`, so
  a naive strip yields "phraseword").
- **TTS round-trip** — invoke the **already-deployed** `nagara-tts` Modal service with `spoken[]`
  (read-only reference dependency — not rebuilt, not modified), zip the returned index-keyed timeline
  onto `display[]` and `spoken[]`, and write the artifact (`display.md`, `spoken.txt`,
  `timeline.json`, the audio file) for inspection.
- **Mandatory synthetic hostile-construct check** — a tiny fixed markdown snippet containing a fenced
  code block (with internal newlines), a blockquote, and an inline link is run through the strip
  **regardless of what the real article contains**, so disproof #5 (code-block fragmentation) and the
  hostile-construct half of disproof #1 (residual syntax) are actually exercised. This is a strip-level
  unit check kept clearly separate from the real-article judgment — the real data still owns the
  verdict; the snippet only ensures the refutation paths aren't no-ops. (It also settles the one
  unconfirmed research point: trafilatura's actual blockquote `>` markdown syntax.)

**Session protocol** (scorable tasks interleaved with reflection):

1. **Markdown direct test** (the agreed first move) — run the markdown extraction on the snapshotted
   fixture and read what it emits: which constructs are present, how inline/links/headings/lists look,
   whether a code block or blockquote appears, and whether the code-block-newline hazard bites here.
   → *reflect*: what does trafilatura markdown actually give for this article, and which of the flagged
   hazards are even in play?
2. **Strip to spoken + integrity** — build the markdown-it-py strip; derive `spoken[]` from
   `display[]`. Check task criteria 1 (clean spoken text) and 2 (structural alignment): no residual
   syntax, links → anchor text, and `display`/`spoken` equal length and index-aligned by construction.
   Then run the **mandatory synthetic hostile-construct snippet** through the same strip and check
   criterion 5 (code block merged atomic, blockquote clean). → *reflect*: is the strip general, or is
   it accreting per-construct special cases; which of the hazardous constructs did the *real* article
   actually contain?
3. **Round-trip through TTS + timing/audio** — send `spoken[]` to the deployed `nagara-tts`, zip the
   index-keyed timeline on, check task criteria 3 (timing invariants) and 4 (clean audio) — listen for
   vocalized syntax — and render `display[]` markdown to confirm it maps 1:1 to the timeline.
   → *reflect*: does the single-extraction / index-keyed model hold end-to-end; where, if anywhere,
   does markdown fight the spoken/timed model?

**Spike location**: `experiments/002-markdown-paragraphs/` — a **self-contained, throwaway** script
with its own env (Python 3.12), snapshotted HTML fixture under `fixtures/`, and outputs written
locally. This is a **deliberate deviation** from the project's spike-at-root, graduate-in-place
convention (see `CLAUDE.md`): the question is a narrow mechanism probe that doesn't need the API/DB/
Modal-spawn machinery, so an isolated sandbox is the cheaper, cleaner fit. It **never imports or
mutates production `api/`**; it reads production only as reference and reuses the *deployed* TTS
service as-is. If (c) proves out, graduation into `api/` is a later, separate rewrite.

## Notes

*(insight log — appended live during `/experiment-run`)*

**2026-07-17 — session 1, task 1 (markdown direct test).** Ran
`trafilatura.extract(output_format="markdown", include_formatting, include_links, include_tables=False)`
on the snapshotted mitchellh fixture (65 KB HTML). Findings that reshape the unit-split design:

- **Markdown mode hard-wraps paragraphs.** 130 non-empty lines vs plain mode's 68 — because a single
  `\n` is a *soft* line break inside a paragraph, not a unit boundary. The real boundary is the **blank
  line** (`\n\s*\n`). Today's `text.split("\n")` (plain path) would fragment every paragraph under
  markdown mode. → the spike splits on blank lines, then joins soft-wraps within a block.
- **Lists are a single blank-delimited block** whose items are separated by single `\n` (e.g. a 3-item
  block: `- a\n- b\n- c`). Naive soft-wrap-join merges them into a run-on; the splitter must break a
  list block into **per-item units**. (Blank-line blocks: 47 raw, but that count wrongly merges list
  items — real unit count is higher once items are split.)
- **Emphasis boundaries drop the surrounding space** — 16 cases like `**Deep research sessions**where`,
  `**Issue and PR triage/review.**A`, `on.**I`. Stripping `**` naively concatenates words
  ("sessionswhere"). markdown-it-py alone doesn't fix it (tokens are `strong` then `text("where")` with
  no whitespace); the plain renderer must **restore a boundary space** at emphasis/text adjacencies.
  This is the load-bearing strip hazard on this fixture (bears on task criterion 1, clean spoken text).
- **Constructs present:** 2 headings, several lists (12 items), ~15 bold, ~16 italic, 8 links. **Absent:
  no fenced code blocks, no blockquotes** — so the hostile constructs the headline question names are
  *not* exercised by this article, exactly the fixture-coverage risk pre-registered. The mandatory
  synthetic snippet is therefore doing real refutation work, not ceremony.
- Minor, consistent with 001: an inline footnote ref renders as a bare `1` ("in a loop 1 At a bare
  minimum") — a known footnote-cruft artifact, backlogged, not fixed here.

*Reflection:* the HTML→markdown boundary isn't the risk here (trafilatura emits coherent markdown); the
risk moved to **segmentation** (blank-line + list-item splitting) and **the strip's word-boundary
restoration**. The single-extraction/index-keyed model is unaffected — display and spoken still derive
from one segmentation.

**2026-07-17 — session 1, task 2 (strip + integrity) + task 3 (TTS round-trip).** Built `pipeline.py`
(split + markdown-it-py strip), `check_synthetic.py`, `run.py`. Discoveries while making the strip clean:

- **CommonMark-invalid run-in bold leaks literal `**`.** trafilatura emits `**Issue and PR
  triage/review.**Agents` — the closing `**` is preceded by punctuation and followed by a letter, which
  fails CommonMark's flanking rule, so markdown-it leaves the markers as literal text (4 units on the
  real fixture). Fix: a **belt-and-suspenders residual pass** — markdown-it does the structural strip
  (links→anchor, valid emphasis, headings, lists, code), then any leftover emphasis marker is turned
  into a space (which also splits the word/sentence trafilatura fused: `review.**Agents` → "review.
  Agents"). Valid emphasis leaves no marker, so the pass is a no-op there.
- **Word-boundary restoration must be CLOSE-side only.** Valid-but-space-dropped emphasis
  (`**sessions**where`) is fixed by inserting a space at the emphasis *close*→text edge when both sides
  are alphanumeric. Doing it at the *open* edge too would over-split intra-word emphasis (`super**b**`
  → "super b"). Close-side only covers the real cases without that artifact (per shape-review).
- **Empty spoken units guarded.** A unit that strips to empty would crash Kokoro / yield a
  zero-duration window and break the index 1:1. Rule: drop empty-spoken units from *both* arrays
  (realign). On this fixture **0 units dropped** — but the guard is in place (per shape-review).
- **Blockquote bug caught by the mandatory synthetic snippet.** The real article has no blockquotes;
  the synthetic snippet exposed that soft-wrap-joining `> ` lines leaks a mid-text `>` into spoken. Fix:
  keep a blockquote block **raw** so markdown-it parses the quote structurally. This is exactly the
  refutation work the snippet was pre-registered to do — the real fixture would never have surfaced it.
- **Code block: atomic, not fragmented (disproof #5 held).** The synthetic fenced block (5 source
  lines) stays **one** unit; spoken = a `"Code sample."` placeholder (reading code aloud is noise — the
  *right* spoken form for code, drop-with-marker vs read-literally, is an open follow-up, not decided
  here). Kept index-aligned.

**2026-07-17 — why trafilatura markdown hard-wraps *some* paragraphs and not others.** Investigated a
question raised on review of `out/full.md`: some paragraphs are one long line, others are hard-wrapped
across several. Root cause — **trafilatura preserves a paragraph's source line breaks only when the `<p>`
contains inline formatting** (em/strong/link); a pure-text `<p>` gets its whitespace normalized to one
line. Across the fixture's 41 body paragraphs: 17 wrapped+has-inline-md, 21 single-line+no-inline-md, and
only 3 exceptions — a strong ~93% correlation. Both paragraphs I diffed had newlines in the *source*
HTML, but only the one containing `*do not*` kept them in the markdown. **This does not affect the
pipeline**: `split_units` joins soft-wraps within a blank-line block, so wrapped and single-line
paragraphs both collapse to one clean unit — which is exactly why "unit boundary = blank line, not `\n`"
was the right call. The `## Table of Contents` orphan heading in `full.md` is the same class of parked
content-cruft: trafilatura lifted the label from the article's collapsible `<details><summary>Table of
Contents</summary><ul>…</ul>` and precision-mode pruned the link list, leaving a bare heading.
Production's `extract.py` drops this exact nav label; the spike deliberately doesn't port that
content-cleanup (faithfulness lens, parked).

**2026-07-17 — heading/nav filtering needs markdown-aware normalization (production impact).**
`check_heading_filter.py` replays production `extract.py::_clean_paragraphs` against the markdown display
units. Result: **production's filter drops 0 units** — `# My AI Adoption Journey` and `## Table of
Contents` survive because its exact-match tests (`low == title_norm`, `low in _NAV_LABELS`) don't see
past the `#`/`##` prefix markdown adds. A **markdown-aware variant** (strip a leading `#{1,6}\s+` / list
marker before comparing) drops both, as intended. Conclusion: **graduation must update `_clean_paragraphs`
to normalize the leading marker before matching** — otherwise the existing title-echo and nav-label
cleanup silently stops working under markdown. Cheap, one-line-ish change; noted for the graduation
follow-up.

**Task 3 round-trip (real fixture → deployed nagara-tts):** 55 units, aligned, **0 dropped**. Timing:
**55 contiguous windows, last `end` == duration (846.23 s ≈ 14 min)** — criterion 3 holds on the
markdown-derived spoken[]. **0 residual markdown syntax across all 55 spoken units** (criterion 1) and
the display↔spoken↔timing zip is coherent (heading `#` dropped, `[Claude Code](url)`→"Claude Code",
run-in bold space restored). Outputs in `out/` (`display.md`, `spoken.txt`, `timeline.json`,
`audio.ogg` 2.3 MB). **Criterion 4 (clean, natural audio) pending the user listen.** Note: minor
content cruft survives (a stray `- ` in "using- gh", a bare footnote `1`) — content-cleanup /
faithfulness lens, parked in `BACKLOG.md`, not a syntax leak.

**2026-07-17 — session 1, raw-vs-clean A/B (disproof #4 counterfactual).** Synthesized 4 syntax-rich
units (`# heading`, `## heading`, a `[text](url)` link, a `- **run-in bold**` list item) as **raw
markdown** vs the **cleaned spoken** form (`run_raw.py` → `out/audio_raw_subset.ogg` /
`audio_clean_subset.ogg`; raw ran 45.8 s vs clean 43.9 s). **User listened: the raw markdown audibly
vocalizes the markdown syntax** — confirming the content MUST be stripped before the TTS service, not
passed through raw. This is the direct, positive confirmation that the strip is load-bearing (disproof
#4 would fire without it), and validates mechanism (c)'s derive-spoken-from-markdown step as necessary,
not incidental.

**2026-07-17 — criterion 4 met; all criteria green.** User confirmed the **cleaned** audio reads as
natural prose with **no vocalized markdown syntax** (criterion 4 ✓). Final scorecard, all against the
real fixture (+ synthetic snippet for the hostile constructs): **1 clean spoken ✓ · 2 alignment ✓ · 3
timing ✓ · 4 clean audio ✓ · 5 code/blockquote strip-level ✓.** None of the five disproof conditions
fired. Insight lens answered: the HTML→markdown boundary was not the risk (trafilatura emits coherent
markdown); the real risks were **segmentation** (blank-line units, list-item + blockquote handling) and
**the spoken strip** (CommonMark-invalid run-in bold, close-side word-boundary restoration) — all
tractable. The single-extraction / index-keyed model made display↔spoken↔timing alignment structural,
needing **no TTS contract change**. Deferred-by-design (not met, honestly): code/blockquote **timing +
audio** round-trip (no fixture exercises them), tables, and the right spoken form for code blocks.
Graduation follow-up surfaced: `_clean_paragraphs` needs markdown-aware marker normalization. Judging
has data against every criterion → ready for `/experiment-conclude`.

**2026-07-17 — conclude-time: effort test for code/blockquote/table cleanup (no audio).** At the user's
request, checked what it takes to strip **all** construct classes correctly (strip-level only), to size
folding them into the promotion:
- **Blockquote** — already correct, zero extra work.
- **Code** — kept atomic; spoken = `"Code sample."` **placeholder accepted as the default for now**
  (user's call); the *right* spoken form for code is deferred to a future experiment (`BACKLOG.md`).
- **Table** — implemented in the spike: detect a table block (don't soft-wrap-join, or `|` pipes leak),
  enable markdown-it's `table` rule, and a ~12-line header-aware linearizer →
  `"Feature: Extraction, Status: done. Feature: Timing, Status: exact."` The *strip* is easy and now
  verified strip-level on the synthetic table. Two caveats keep it from being "done": extraction runs
  `include_tables=False` today (a trafilatura precision trade-off — tables aren't even emitted unless
  flipped), and no real fixture validated tables end-to-end (audio+timing). One bug found+fixed en
  route: the table router matched the whole multi-line unit (`$` mid-string) and fell through to the
  inline walker, concatenating cells (`FeatureStatusExtractiondone…`) — fixed by matching the first
  line. Net: the markdown→spoken transformation is tractable for every construct; tables' *extraction
  toggle* and end-to-end validation remain the real follow-up work.

## Verdict

**PROMOTE.** Markdown can be carried through the pipeline to the render layer while keeping Kokoro's
audio clean and paragraph timing exact — via a **single markdown extraction** whose spoken text is
*derived* from it, with the TTS returning **index-keyed** timing that zips onto both arrays. All five
task criteria met and none of the five disproof conditions fired: 55 aligned units with 0 residual
markdown syntax, timing monotonic/contiguous with last `end` == duration (846.23 s), and user-confirmed
clean, natural audio. The raw-vs-clean A/B positively confirmed the strip is load-bearing (Kokoro
audibly vocalizes syntax when fed raw markdown). Critically, the mechanism needed **no TTS/Modal
contract change** — the service was already index-keyed.

The insight lens paid off: the HTML→markdown boundary was *not* the risk (trafilatura emits coherent
markdown); the real risks were **segmentation** (markdown hard-wraps, so unit boundary = blank line;
lists split per-item; blockquotes/tables kept raw) and **the spoken strip** (CommonMark-invalid run-in
bold leaking `**`; close-side-only word-boundary restoration). All proved tractable. The mandatory
synthetic snippet earned its place — it caught a blockquote `>` leak the real (blockquote-free) article
never could.

**Scope**: self-use, Nagara only, **one** clean-HTML article (Mitchell Hashimoto) end-to-end, plus a
synthetic snippet for the constructs it lacked. **End-to-end proven (audio + timing)**: inline emphasis,
links, headings, lists. **Strip-level only** (no audio/timing round-trip): blockquote, code, table —
and tables additionally need `include_tables=True`, an extraction-side precision trade-off not exercised
here. Not evidence of generalization across article types/formatting density, of demand, or of the
player UX. Content-cleanup (echoed title, nav labels, footnote cruft) was deliberately out of scope.

**Decision**: **Promote the whole feature** to a new `PRODUCT.md` milestone (markdown-formatted
read-along content) — the complete markdown capability across **all seven construct classes** (inline
emphasis, links, headings, lists, blockquotes, code, tables); the spike implements and strip-verifies
every one. Graduation is a rewrite into `api/` (single markdown extraction + spoken strip + index-keyed
zip; the spike at `experiments/002-markdown-paragraphs/` is reference, not copied). The spoken
*transformation* is proven for every construct; but the integrity round-trip (audio + timing) for
blockquote/code/table is **unproven** — for those constructs the core "does it break TTS/timing" question
is not yet answered end-to-end, and that is the promoted feature's largest open validation risk. Routed
to `BACKLOG.md`: validate blockquote/code/table **end-to-end** (audio + timing) on a formatting-heavy
fixture and turn on `include_tables`; settle the
right spoken form for code blocks (placeholder is the interim default); and make `_clean_paragraphs`
markdown-aware (its exact-match title/nav cleanup silently stops firing once markers are present).
Process learning (pre-register a synthetic probe when the real artifact can't exercise a disproof
condition) routed into the project's `.zenku/experiment-start.md` extension.
