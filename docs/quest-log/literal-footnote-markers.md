---
title: "Literal footnote markers read aloud"
tags:
  - quest
summary: "A footnote marker written as plain text carries no markup to prune, so it survives to synthesis and is read aloud."
status: open
kind: build
adventure:
blocked_by: []
priority: 3-later
created: "2026-08-30"
---

# Literal footnote markers read aloud

## What

Footnote reference markers are stripped structurally, by pruning the markup that identifies them out of the HTML before extraction. A marker with no markup around it is outside that reach and still gets spoken: a `[1]` typed into the prose as ordinary text, and a bare digit left behind by a shape the xpath list does not enumerate.

The bracketed case is recoverable at the text layer. The bare-digit case is not: `"if AI is here to stay 3, I'm a software craftsman"` and `"Simultaneous to step 5, I'm also operating"` are the same shape as text, so a rule that removes one removes the other.

## Design

A residual strip over the spoken path, on `text` tokens inside `_to_spoken` so an inline code span and a fenced block are protected by the token walk rather than by a guard.

Two calls already settled, so they do not get re-litigated:

- **Cap at one to three digits.** `[1]`, `[12]`, `[123]` and runs like `[1][2]` strip. `[1997]` does not: four digits is a year or a figure number.
- **Unicode superscripts (`¹²³`) are left alone.** They read as unambiguous and are not: `m⁻¹`, `x²` and `km h⁻¹` are prose-meaningful in scientific writing.

Left alone either way: any brackets holding a letter (`[sic]`, `[citation needed]`, `[Knuth 1984]`), and the bare-digit case above.

Worth settling first: whether this is worth building at all before an article that actually exhibits it is in the corpus. Every real fixture so far carries markup.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]]
