# Feature Spec — Markdown-formatted read-along content

**Status**: ✓ current **Roadmap**: [Milestone 2 / `markdown-read-along-content`](../planning/ROADMAP.md) **Grounded in**: [experiment 002](../../experiments/002-markdown-paragraphs/README.md), `LEARNINGS.md` 2026-07-17 — 002

Paragraphs carry their formatting to the render layer while the spoken audio stays clean. A `ready` item's display paragraphs are markdown; the audio is generated from a plain-text form derived by stripping that markdown, and the read-along timeline aligns to both by position. A paragraph has both a *display* form (markdown) and a *spoken* form (plain text), joined by index — while the enqueue → eager-generate → pollable-item shape, the timing invariants, auth, and audio delivery of the backend spine hold unchanged. What follows is the present intent of the feature — the behavior it guarantees and the boundaries it holds.

## User story

As an API consumer (a future read-along web player, or an agent such as Tachikoma), I want each paragraph of a `ready` item to carry its markdown formatting for display while the audio and timing stay clean and aligned, so that the player can render emphasis, links, headings, lists, quotes, code, and tables without the audio ever speaking the syntax and without reconciling two separate paragraph lists.

## Requirements

Prioritized problem-space summary. Each requirement links the evidence that justifies it. Status: `Core goal` / `Must-have` / `Nice-to-have` / `Out`.

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| R1 | A `ready` item's paragraphs carry a **display** form that preserves the article's markdown formatting, distinct from the **spoken** form that drives the audio | Core goal | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R2 | The spoken form is **derived from** the display markdown by stripping syntax; the generated audio never vocalizes markdown markers and reads as natural prose | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md), `LEARNINGS.md` 002 |
| R3 | Display, spoken, and the timing window for a paragraph are aligned **1:1 by position** — one extraction is the source of truth, so alignment is structural, not a reconciliation step; the three lists are equal length and index `i` refers to the same logical unit in all three | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R4 | Formatting is carried across all seven construct classes: inline emphasis, links, headings, lists, blockquotes, code blocks, and tables. Links reduce to their anchor text (URL dropped) in the spoken form; a code block reads as a short placeholder; a table reads as header-aware prose. Inline emphasis, links, headings, and lists are proven end-to-end (audio + timing); blockquote, code, and table are proven at the strip level only — their audio + timing round-trip is an open validation risk (see Unknowns) | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R5 | Paragraph segmentation matches the article's logical units: a paragraph is one display unit (its soft-wraps joined), each list item is its own unit, a code block is one atomic unit, and a blockquote or table block is one unit | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R6 | A unit whose spoken form is empty (e.g. an image-only unit) is dropped from **both** the display and spoken lists, so the index alignment holds and no empty text is ever sent for synthesis | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R7 | The read-along timeline over the derived spoken text keeps the existing timing invariants: windows are monotonic, non-overlapping, contiguous, and the last window ends at the audio's total duration | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md), `LEARNINGS.md` 001 |
| R8 | Edge cleanup (echoed title, navigation labels, footnote glyphs, punctuation-only artifacts) stays effective when paragraphs carry markdown — a leading formatting marker must not defeat the title/nav match | Must-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |
| R9 | Generating markdown-formatted content requires **no change to the TTS contract** — the spoken list is synthesized by the existing service and its position-keyed timeline joins back onto both lists | Nice-to-have | [exp 002](../../experiments/002-markdown-paragraphs/README.md) |

Requirements state WHAT is needed. Acceptance criteria define HOW to verify each.

## Acceptance criteria

- **R1** — Given a `ready` item whose article contains formatting, When it is read, Then each paragraph exposes a display form that retains the markdown (e.g. emphasis markers, a heading prefix, a link) and a distinct plain spoken form, and the two are individually observable.
- **R2** — Given a paragraph with inline emphasis, a link, a heading, or a list marker, When its spoken form is inspected, Then it contains no markdown syntax (`* _ # [ ] (url) ` `` ` `` ` > |`), a link is reduced to its anchor text with the URL absent, and a word boundary dropped at a run-in emphasis (`**phrase**word`) is restored (`phrase word`); and Given the item's audio, When it is played, Then no markdown syntax is heard and it reads as natural prose.
- **R3** — Given a `ready` markdown item, When its display list, spoken list, and timing windows are compared, Then all three are the same length and, for every index `i`, the display unit, its spoken text, and its timing window describe the same logical paragraph — zipping by index yields a coherent per-unit `{display, spoken, start, end}` with no reconciliation.
- **R4** — Given an article containing each construct class, When it is processed, Then: inline emphasis keeps its text and drops its markers; a link keeps its anchor text and drops its URL; a heading keeps its text and drops the `#` prefix; each list item is a unit with its bullet/number marker dropped from the spoken form; a blockquote reads as clean prose without a leading `>`; a code block is one unit whose spoken form is a short placeholder rather than the code read aloud; and a table reads as header-aware prose (`Col: value, Col: value.`) rather than pipe characters.
- **R5** — Given article markdown, When it is segmented, Then a multi-line paragraph collapses to one unit (soft-wraps joined), a three-item list yields three units, a fenced code block stays a single unit with its internal newlines intact, and a blockquote or table block is a single unit — the unit boundaries match the article's logical structure, not raw line breaks.
- **R6** — Given a unit that strips to empty spoken text, When the content is assembled, Then that unit appears in neither the display nor the spoken list, the remaining indices stay contiguous, and no empty string is submitted for synthesis.
- **Degenerate case** — Given an article with no formatting at all, When it is processed, Then each paragraph's display form equals its spoken form, alignment and timing still hold, and the item is indistinguishable in behavior from a backend-spine item — carrying markdown never regresses the plain-text path.
- **R7** — Given a `ready` markdown item's timing windows, When inspected in order, Then each window's start equals the previous window's end and the last window's end equals the reported audio duration.
- **R8** — Given an article whose extraction echoes the title or a navigation label as a markdown heading or list item, When the content is cleaned, Then that unit is dropped just as it is for a plain-text article — the leading marker does not cause the cleanup to silently pass it through.
- **R9** — Given the content-generation path, When an item is synthesized, Then the request sent to the TTS service and the shape it returns are the same as for a non-markdown item — the markdown capability adds no field to and requires no change of the synthesis contract.

## Open questions / unknowns

- **End-to-end validation of blockquote, code, and table is thin.** The spoken *transformation* is verified for all seven construct classes, but only inline emphasis, links, headings, and lists were carried all the way through audio + timing on a real article; blockquote, code, and table were verified at the strip level only. Their audio + timing round-trip is the feature's largest open validation risk; a formatting-heavy end-to-end validation is tracked in `BACKLOG.md`. Resolve in `/design` how far this feature validates them versus leaving the round-trip to that follow-up.
- **Tables require enabling table extraction.** Emitting tables at all means turning on table extraction, which today is off as a precision trade-off — a genuine extraction-side decision to settle in `/design`: whether flipping it is acceptable for the whole pipeline, or tables are gated behind it.
- **The right spoken form for a code block is unsettled.** A short placeholder is the accepted interim; whether code should instead be summarized, read literally, or handled another way is a parked follow-up in `BACKLOG.md` — not decided here.
- **Nested lists.** Each list item is its own unit, but how a nested (indented) sub-list segments — its own units, or folded into the parent item — is unspecified; the real article exercised only flat lists. To settle against the formatting-heavy fixture in `/design` or its `BACKLOG.md` follow-up.

## Out of scope

- **Content-cleanup / faithfulness beyond edge cruft** — stray inline artifacts (a bare footnote number, a leftover list dash inside prose) and prose-boilerplate stripping are a separate concern already parked in `BACKLOG.md`; this feature does not improve extraction faithfulness, only carries formatting cleanly.
- **The read-along player UX** — how a client renders the markdown (which formatting it honors, styling) is the web-player slice, not this feature; this feature only guarantees the display markdown is present and aligned.
- **Word-level timing** — paragraph-level only, unchanged from the backend spine.
- **Deciding the definitive spoken form for code blocks and the end-to-end table validation** — parked follow-ups (see Unknowns), not built here beyond the interim behavior.

## Dependencies

- [`enqueue-to-audio-api`](enqueue-to-audio-api.md) (Milestone 1) — this feature evolves that pipeline's extraction step and item/read-along contract; the enqueue → eager-generate → pollable-item shape, the timing invariants, auth, and audio delivery are inherited unchanged. (Roadmap ordering: [`docs/planning/ROADMAP.md`](../planning/ROADMAP.md).)
