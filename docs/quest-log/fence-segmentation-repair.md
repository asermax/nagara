---
title: "Fence segmentation repair"
tags:
  - quest
summary: "An unbalanced fence count swallows two thirds of one article's prose and speaks it as \"Code sample.\" three times; two independent causes, two different fixes."
status: solved
kind: build
adventure: richer-extraction
blocked_by:
  - typed-unit-contract
priority: 2-soon
created: "2026-08-02"
---

# Fence segmentation repair

## What

On `realpython.com/python-first-steps/`, more than half the article body is silently replaced by the words "Code sample."

Trafilatura emits 151 fence lines. `_repair_inline_fences` collapses three inline-code artifacts, leaving 145, still odd and still unbalanced. From the first unmatched fence onward `_blocks()` keeps `in_fence` toggled the wrong way and consumes everything until the next fence line, whatever it is. Three "code blocks" come out mostly article prose: 11,159 chars, 9,265 chars, 2,264 chars. Roughly 3,687 words against the article's 6,543.

Every one reaches `_to_spoken`, matches `_FENCE`, and returns the literal string `"Code sample."`

Nothing caught it. Extraction does not raise, the unit count looks healthy at 359, the item reaches `ready`, and the audio is fluent. A listener hears "Code sample." three times where two thirds of the tutorial should be. This is the project's standing failure shape: invisible in a diff, invisible in a test summary, obvious in ten seconds of audio nobody had played.

After this quest, enqueue that article and hear the article.

## Design

### Two independent causes, and neither is the one the diagnosis expected

Diagnosed against the cached corpus HTML with `markdown_it` as the CommonMark ground truth.

| Cause | Words | What catches it |
|---|---|---|
| trafilatura wraps prose in **closed** fences | 2,223 | only a content guard |
| one genuinely **unclosed** fence, opens at line 1301 and runs to EOF | 1,464 | the structural fix |
| interior fence-like lines desync the toggle: a traceback caret `~~~^~~`, an indented literal | ~320 | the structural fix |

The three big closed-prose blocks are *structurally* code blocks. Trafilatura fenced the prose, and no parser recovers them, CommonMark-faithful or otherwise.

### Fix one, structural

Keep the hand-rolled `_blocks` toggle. Two surgical changes, both CommonMark-correct.

**Tighten `_FENCE` from `^\s*(```|~~~)` to `^[ ]{0,3}(```|~~~)`.** CommonMark allows at most three leading spaces before an opening fence. `\s*` matches indented literals and indented traceback carets, and both desync the toggle.

**Refuse to open a fence that has no closer anywhere after it**, emitting the opener line as prose. This is the safe recovery: it touches only a genuinely unclosed fence and recovers its 1,464 words.

### Fix two, the content guard

Detect a fenced block whose interior is mostly sentence-shaped prose (prose-prefixed lines, none of `>>>`, `$`, `#`, `//`) and **re-classify it as a paragraph unit**, stripping the fences. The listener then hears the actual article text and the 2,223 words arrive. This is the loudest non-failure available.

The detector must leave real REPL transcripts as code. The exact threshold is a build decision made against fixtures.

The re-classification flips a unit's type from `code` to `paragraph` at extraction time, which is why this quest is blocked by [[typed-unit-contract]]: the discriminator is assigned after the guard runs, not directly in `_split_units`.

### Rejected, on evidence

**Delegate segmentation to `markdown_it` token maps.** Correct-by-construction for fences, but the prototype roughly doubles unit counts on every article (359 to 610 on realpython, 75 to 143 on ACX) because its list-item flattening and paragraph handling differ from `_split_units`. That is a separate blast radius over the whole unit contract, and it does not catch the fenced-prose cause either, since `markdown_it` also sees those as code blocks.

**The blank-line recovery anchor**, refusing to open a fence with no closer before the next blank line. It recovers the most words, and 6 of 72 real code blocks on this article contain internal blank lines, so it drops real code.

### What this unblocks

[[describe-code-blocks]] is downstream of this and cannot be built first. With both fixes in place, the only units reaching the describer are genuinely code: the unclosed fence becomes prose at the parse layer, and closed fenced-prose is re-classified before synthesis.

The original describer bake-off picked "the largest fenced unit in the corpus" as its test case, and that unit is one of the fenced-prose blocks this quest re-classifies. Any re-bake-off must select code from the post-fix population and not inherit that sample.

### How it is verified

Seam 2, `units_from_markdown`, with fixtures. Per `CLAUDE.md` an extraction rule owes a function, a case in `test_extract.py`, and a fixture.

**The fixture is load-bearing and cannot be synthesized down.** This bug is only visible with the real ~300 KB document, cached at `prototype_cache/t17_realpython.html` on `idea/firecrawl-markdown-fidelity`.

Plus a callout in [[article-extraction]] explaining why the toggle refuses an unclosed opener, and why a guard looks at content at all.

### What this does not settle

Whether a *pattern* of fenced-prose across an article, as a signal that extraction is degraded, should trigger document-level escalation to the firecrawl fallback. Only one corpus article fences prose at all, so incidence is unknowable until a second code-heavy article exists. Fog, deliberately not a quest.

---

Related: [[quest-log/README|the quest log]] · [[richer-extraction]] · [[article-extraction]] · [[typed-unit-contract]] · [[describe-code-blocks]] · [[trustworthy-extraction]]
