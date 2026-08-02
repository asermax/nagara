---
title: "Markdown-formatted paragraphs"
tags:
  - quest
summary: "Show a paragraph with its real formatting (emphasis, links, headings, lists, quotes, code, tables) while the audio stays clean prose and the highlight stays exactly on what is read."
status: solved
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Markdown-formatted paragraphs

## What

Show a paragraph with its real formatting (emphasis, links, headings, lists, quotes, code, tables) while the audio stays clean prose and the highlight stays exactly on what is being read. Already true of the code: the TTS returns its timing keyed by list position, which is the seam this builds on.

## Answer

**Promoted: the whole markdown capability, all seven construct classes.** Built in place at `api/app/service/extract.py` and `api/app/helpers.py`; the spike (`experiments/002-markdown-paragraphs/`) was reference material and the graduation was a rewrite. Where it lives: [[article-extraction]], [[item-contract]].

De-risked by [[markdown-paragraph-pipeline]], which cleared every unknown it carried:

- Spoken text can be stripped clean of markdown generally, without per-article special-casing: **yes**, a markdown-it-py token walk with two non-obvious repairs: word-boundary restoration close-side only (open-side over-splits `super**b**`), and a residual pass because trafilatura emits CommonMark-invalid run-in bold the parser leaves as literal `**`.
- No construct forces display and spoken apart so the 1:1 index breaks: **correct, given one segmentation.** The unit boundary is the blank line (markdown mode hard-wraps); lists split per item (including a nested sub-item, which becomes its own unit); blockquote and table blocks are kept raw; empty-spoken units drop from both lists.
- Carrying markdown does not regress the timing invariants: **correct.** 55 aligned units, contiguous windows, last `end` == duration (846.23 s).
- The TTS contract does not change: **correct**, it was already index-keyed.

What was accepted, not cleared: the audio + timing round-trip is proven strip-level only for blockquote, code, and table (the real fixture carried none; tables additionally need `include_tables=True`, on in production but never validated end-to-end); and the right spoken form for a code block is still open (a short placeholder is the interim; an LLM-produced short explanation is the promising direction).

> [!note] Promoted over three open unknowns, accepted rather than cleared
> The spoken *transformation* is proven for every construct class; the audio + timing round-trip is not proven for blockquote, code, or table. This is the feature's largest open validation risk, carried knowingly rather than blocking the promotion.

How far the evidence reaches: one clean-HTML article end-to-end, plus a synthetic snippet for the constructs the article lacked; not evidence of generalization across article types or formatting density.

---

Related: [[quest-log/README|the quest log]] · [[markdown-paragraph-pipeline]] · [[article-extraction]] · [[item-contract]] · [[prose-boilerplate-stripping]] · [[markdown-faithfulness-and-worth-it]]
