# ADR-007 — Markdown as the extraction source of truth (single extraction, derived spoken, index-keyed)

**Status**: Accepted **Date**: 2026-07-17 **Grounded in**: [experiment 002](../../experiments/002-markdown-paragraphs/README.md)

## Context

Paragraphs must reach the render layer carrying their formatting (emphasis, links, headings, lists, quotes, code, tables) so a read-along player can display them richly — while the generated audio stays clean, never speaking the syntax, and the per-paragraph timing stays exactly aligned to what is shown. The danger is that the *displayed* text and the *spoken/timed* text drift apart and need reconciling.

Two extraction passes — one plain for audio, one markdown for display — would diverge: the underlying extractor segments from the document tree, and toggles like table and link inclusion are tree-shape decisions, so two independent passes produce different unit counts and boundaries exactly when an article has richer structure. That manufactures the alignment problem this decision exists to avoid.

The text-to-speech service already returns its timing keyed by **list position** (`{index, start, end}` per submitted paragraph), not by matching text back. That position key is the seam that makes a single-extraction approach clean.

## Decision

Extraction produces **one markdown document as the single source of truth**, from which two aligned lists are derived by one segmentation:

- a **display** list — the markdown units a client renders, and
- a **spoken** list — each unit with its markdown stripped to clean prose (emphasis reduced to its text, a link to its anchor text with the URL dropped, heading/list markers removed, a code block replaced by a short placeholder, a table linearized to header-aware prose).

Because both lists come from one segmentation, `display[i]` and `spoken[i]` are the same logical unit by construction. The spoken list is submitted to the **unchanged** text-to-speech service, and its position-keyed timeline joins back onto both lists **by index** — alignment is structural, never reconciled. This requires **no change to the text-to-speech contract**.

This **builds on ADR-004** (server-side fetch + trafilatura, headless deferred): the fetch-and-extract foundation is unchanged; this decision fixes the extractor's *output* as markdown and adds the derive-spoken step. **Table extraction is enabled** so tables can be carried and linearized (a precision trade-off accepted at the extraction layer).

## Consequences

- **Alignment is structural.** One segmentation means display, spoken, and timing share one index; there is no text-matching or reconciliation step, and no class of article can silently split the two apart.
- **No text-to-speech contract change.** The service stays index-keyed and untouched; the whole capability lives in the API's extraction and content-assembly layer.
- **The display/spoken split becomes the content contract** every downstream surface consumes (the read-along player, and later caption export). It is hard to reverse once clients build on markdown display.
- **Both derived forms must be robust to imperfect markdown** the extractor emits (e.g. run-in emphasis that is technically invalid syntax), not just well-formed markdown: the spoken strip absorbs it into clean prose, and the display markdown is repaired to valid, renderable markdown (emphasis boundaries fixed) before it is persisted as the unit's `text`.
- **Enabling table extraction trades some precision** across all articles (table-shaped non-content may occasionally be pulled in), accepted to carry tables at all.
- **A validation gap is inherited**: inline emphasis, links, headings, and lists are proven end-to-end (audio + timing); blockquote, code, and table are proven at the strip level only. The audio + timing round-trip for those three is tracked as a follow-up in `BACKLOG.md`.

## Alternatives considered and not chosen

- **Dual extraction** (a plain pass for audio + a markdown pass for display, then reconcile) — not chosen: tree-driven segmentation makes the two passes diverge whenever an article has richer structure (notably tables), recreating the exact alignment risk this avoids.
- **Single markdown extraction with text-keyed timing** (match the timeline back to units by text) — not chosen: it re-derives a text-matching join the text-to-speech service does not need, since it already returns timing by position.
- **Keeping plain-text extraction and adding formatting later** — not chosen: formatting is a tree-level property of the same extraction; recovering it after flattening to plain text is lossy and would still face the divergence problem.
