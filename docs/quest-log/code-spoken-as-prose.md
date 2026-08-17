---
title: "Code spoken as prose"
tags:
  - quest
summary: "On a pathologically-fenced tutorial, trafilatura flattens REPL and code into inline-code spans inside prose paragraphs, so a listener hears code read as prose."
status: open
kind: design
adventure:
blocked_by: []
priority: 2-soon
created: "2026-08-16"
---

# Code spoken as prose

## What

On a code-heavy tutorial, some code reaches the listener spoken as prose: a REPL transcript reads out as `>>> # Floating-point numbers >>> int(10.6) 10 ...`, and a code line reads out with its inline comment, `greeting = "Hello, World!" # This is an inline comment`. The reader still sees the code correctly; only the spoken form is wrong.

Found by ear on `realpython.com/python-first-steps/`. The listener does not hear a markdown marker, so this is not the two-guard describer concern; it is code that never became a code unit and so was never described or placeheld.

## The root cause

These units are **not fenced**. trafilatura rendered multi-statement REPL and code as one large **inline `code` span inside a prose paragraph**, mixing an intro sentence with the code: `` `10.6` returns `10` instead of `11`. Likewise, `3.25` returns `3`: `>>> # Floating-point numbers >>> int(10.6) 10 ...` ``.

`_to_spoken` unwraps an inline `code` token by emitting its content, which correctly drops the backticks, so no marker leaks. But the content it emits is the code itself, `>>>` prompts and `#` comments and statements, and that is spoken as prose. Because the block never matched a fence, nothing tagged it `code`, so it was neither described nor reduced to a placeholder.

This is the residue of the same pathological fences the fence-segmentation-repair work navigated: on this one article trafilatura's code output is unbalanced and partly flattened. Only one corpus article does this, so incidence past it is unknown.

## Why sanitize does not fix it

`sanitize_spoken` strips markdown markers, and it already runs on this path. The problem is not a marker; it is that genuine code content sits inside a prose paragraph, interleaved with real prose in the same unit. There is no marker to strip and no clean seam to split on: `10.6 returns 10 instead of 11. Likewise, 3.25 returns 3:` is prose, and the REPL that follows it is code, in one paragraph.

## What this quest has to decide

The approach is undesigned. Open questions:

- **Detection.** How to recognize a prose paragraph that carries flattened REPL or code, without misfiring on prose that legitimately quotes a symbol or a short expression. A large inline-code span, or one carrying `>>>`/`$`/multiple statements, is a candidate signal.
- **Handling.** Once detected, whether to split the code out into its own unit (so the describer names it) or reduce the inline code to a short placeholder, and how to do either when prose and code share one paragraph.
- **Scope.** Whether this is worth solving before a second code-heavy article exists to measure incidence, or whether it stays a documented limitation until then.

Judge it against the cached corpus HTML for that article rather than in the abstract.

## How it was found

Surfaced during the richer-extraction listen pass, which generated the two corpus articles through the real Modal path and scanned every spoken form. A sibling finding on the same run, a table cell reading its inline-code backtick, was a clean sanitize gap and was fixed at the table path. This one is separate and deeper, which is why it is its own quest.

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[trustworthy-extraction]]
