---
title: "Raw math delimiters"
tags:
  - quest
summary: "Third slice: recover math/tex scripts and gated raw LaTeX delimiters, killing the two families a listener currently hears as syntax."
status: open
kind: build
adventure: formulas-read-aloud
blocked_by:
  - mathml-recovered-and-spoken
priority: 1-now
created: "2026-08-30"
---

# Raw math delimiters

## What

The two remaining sources, and the half of this raid that fixes the families where a listener currently hears **fluent-looking garbage** rather than silence: `$\mathbf{x}$` read as "dollar backslash mathbf x dollar", and `\(x_t\)` read as "(x underscore t)". It adds `<script type="math/tex">` and the raw-delimiter text-node path behind `declares_math_renderer` to the `carry_math` built by [[mathml-recovered-and-spoken]].

It carries `1-now` alongside the first slice, ahead of [[described-display-formulas]], because a wrong reading is worse than an unimproved one: those two families are actively speaking syntax at a listener today, while a formula floored to verbalized LaTeX is already correct and merely unpolished.

## Design

The shape is settled on [[latex-formulas-not-read]], stage 1, sources 2 and 3. What follows is what this slice takes from it and the one thing the muster found missing that will eat a code block if nobody builds it.

### What this slice builds

**`declares_math_renderer(tree: HtmlElement) -> bool`** in `formulas.py`: true when the page loads MathJax or KaTeX, or carries their configuration. Both leak-family probes carry one (lilianweng three occurrences, colah eight); the MathML families do not need it.

**Source 2, ungated.** `<script type="math/tex">` and `<script type="math/tex; mode=display">`, MathJax v2's pre-typeset form. The type attribute identifies it unambiguously, so no gate is needed.

**Source 3, gated.** Raw delimiters in text nodes: `$…$`, `$$…$$`, `\(…\)`, `\[…\]`, behind `declares_math_renderer`, plus the per-candidate shape guard the design specifies even when the gate passes: the body must carry a LaTeX signal (a backslash command, `^`, `_`, or `{`) and must not span a blank line.

**The precedence order matters here and only here.** Source 1 before 2 before 3, so a page carrying both a `<math>` twin and the `math/tex` source script that produced it recovers once rather than twice.

### The skip list, which the design does not have and which this slice needs

The text-node walk **must skip `<pre>`, `<code>`, `<script>` other than the `math/tex` types, `<style>`, `<kbd>` and `<samp>`.**

This is not defensive tidiness. lilianweng is a page that declares MathJax **and** carries code blocks. A shell line containing `${HOME}`, or a snippet with `$foo_bar`, passes the renderer gate (the page declares one) and passes the shape guard (`{` and `_` are both LaTeX signals). Without a skip list the recovery rewrites a code block's contents into a math carrier, which then reads aloud as a verbalized formula. The failure lands on the exact article this slice's headline fixture comes from.

Build the skip list, and put the negative case in the fixtures rather than trusting it.

### The `\(…\)` mangling disappears by construction

`_to_spoken` currently eats `\(` as a CommonMark escape, leaving `(x_t)`. On a page that declares a renderer, the gate and carrier convert `\(x_t\)` into a carrier while it is still HTML, so markdown-it never sees `\(` and the silent misreading cannot happen. On a page that declares no renderer, `\(` still reaches `_to_spoken` and is still read as an escaped paren, and that is accepted: there the construct is far likelier to be a literal escaped parenthesis than math. No new guard is added for it.

### Record what the cap actually does on this article

lilianweng recovers 24 display formulas against a `describe_max_per_item` of 25, so once this and [[described-display-formulas]] are both in, formulas take almost the whole describe budget on that article and its code blocks floor. Write the observed number down in the answer.

Do not fix it here. The shared budget starving a later kind, and the code-outage guard not firing when it happens, are pre-existing behaviour tracked by the loose quest `describe-budget-starves-later-kinds` (named, not linked: it outlives this effort). This slice owes it one measurement, not a decision.

### Fixtures

One per family this slice covers, with cases in `test_extract.py`:

- **`$$…$$` inside a bare `<div>`**, lilianweng: 24 display formulas where the block used to vanish behind `favor_precision`.
- **The `$…$` leak**, lilianweng: literal `$\mathbf{x}$` reaching both `display` and `spoken` today.
- **The `\(…\)` leak**, colah: `\(x_t\)`, mangled to `(x_t)` by the CommonMark escape today.

Plus two negative cases, because the whole design of the gate is what they test:

- **Currency on a page that declares a renderer.** "between $5 and $10 million" must survive untouched: the shape guard is what saves it, since the gate is open.
- **A code block on a page that declares a renderer.** A `${HOME}` or `$foo_bar` inside `<pre>`/`<code>` must survive untouched: the skip list is what saves it.

### Done when

"dollar backslash mathbf x dollar" and "(x underscore t)" are gone from the two leak fixtures, lilianweng's 24 display formulas exist as `FormulaUnit`s, currency survives, a code block survives, the cap-crowding number is written down, and `uv run pytest` / `uv run ruff check` / `uv run ty check` are green in `api/`.

**And it has been played.** One formula from each leak family, listened to, because the whole point of this slice is what a listener hears.

---

Related: [[quest-log/README|the quest log]] · [[formulas-read-aloud]] · [[latex-formulas-not-read]] · [[mathml-recovered-and-spoken]] · [[described-display-formulas]]
