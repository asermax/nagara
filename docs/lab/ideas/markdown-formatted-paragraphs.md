---
title: "Markdown-formatted paragraphs"
tags:
  - idea
summary: "Show a paragraph with its real formatting (emphasis, links, headings, lists, quotes, code, tables) while the audio stays clean prose and the highlight stays exactly on what is read."
status: promoted
priority: next
impact: high
size: medium
experiments:
  - "[[markdown-paragraph-pipeline]]"
---

# Markdown-formatted paragraphs

## Objective

Show a paragraph with its real formatting (emphasis, links, headings, lists, quotes, code, tables) while the audio stays clean prose and the highlight stays exactly on what is being read. Already true of the code: the TTS returns its timing keyed by list position, which is the seam this builds on.

## Unknowns

- ~~Can spoken text be stripped clean of markdown generally, without per-article special-casing?~~ → **Yes**, a markdown-it-py token walk, with two non-obvious repairs: word-boundary restoration **close-side only** (open-side over-splits `super**b**`), and a residual pass because trafilatura emits CommonMark-*invalid* run-in bold the parser leaves as literal `**`. [[markdown-paragraph-pipeline]]
- ~~Does any construct force display and spoken apart so the 1:1 index breaks?~~ → **No, given one segmentation.** The unit boundary is the blank line (markdown mode hard-wraps), lists split per item (including a nested sub-item, which becomes its own unit), blockquote and table blocks are kept raw, and empty-spoken units are dropped from both lists. [[markdown-paragraph-pipeline]]
- ~~Does carrying markdown regress the timing invariants?~~ → **No.** 55 aligned units, contiguous windows, last `end` == duration (846.23 s). [[markdown-paragraph-pipeline]]
- ~~Does the TTS contract have to change?~~ → **No**: it was already index-keyed. [[markdown-paragraph-pipeline]]
- Still open: does the audio + timing round-trip hold for blockquote, code and table? Verified strip-level only in [[markdown-paragraph-pipeline]]; the real fixture carried no blockquote and no table, and tables additionally need `include_tables=True`, which is on in production but has never been validated end-to-end.
- Still open: what is the right spoken form for a code block? A short placeholder is the interim; an LLM-produced short explanation is the promising direction.

> [!note] Promoted over three open unknowns, accepted rather than cleared
> The spoken *transformation* is proven for every construct class; the audio + timing round-trip is not proven for blockquote, code, or table. This is the feature's largest open validation risk, carried knowingly rather than blocking the promotion.

## Conclusion

**Promoted: the whole markdown capability, all seven construct classes.** Built in place at `api/app/service/extract.py` and `api/app/helpers.py`; the spike (`experiments/002-markdown-paragraphs/`) was reference material and the graduation was a rewrite. Where it lives: [[article-extraction]], [[item-contract]].

What was accepted, not cleared: the three unknowns above. How far the evidence reaches: one clean-HTML article end-to-end, plus a synthetic snippet for the constructs the article lacked; not evidence of generalization across article types or formatting density.

---

Related: [[lab/README|the lab]] · [[markdown-paragraph-pipeline]] · [[article-extraction]] · [[item-contract]] · [[prose-boilerplate-stripping]] · [[markdown-faithfulness-and-worth-it]]
