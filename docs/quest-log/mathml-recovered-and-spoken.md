---
title: "MathML recovered and spoken"
tags:
  - quest
summary: "First slice: carry <math> through the extraction seam into a FormulaUnit, display it as raw LaTeX and speak it with the verbalizer."
status: open
kind: build
adventure: formulas-read-aloud
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# MathML recovered and spoken

## What

The first vertical slice, and the one every other slice sits on. Recover `<math>` elements at the extraction seam so a formula stops vanishing, carry it to a fourth typed unit, render it as raw LaTeX for a client and speak it with the verbalizer. arXiv HTML, Wikipedia and server-prerendered KaTeX read end to end when this lands. No describer: the spoken form is the verbalized LaTeX, which the next slice upgrades.

## Design

The shape is settled on [[latex-formulas-not-read]] and is not restated here. What follows is what this slice takes from it, plus what the muster found the design does not cover.

### What this slice builds

**`api/app/service/formulas.py`**, new, carrying `carry_math(html: str) -> str` and `verbalize(tex: str) -> str`. `declares_math_renderer` is **not** built here: it gates a source this slice does not add, and it belongs with that source on [[raw-math-delimiters]].

**`carry_math` handles source 1 only.** `<math>` elements: TeX out of `<annotation encoding="application/x-tex">`, else the `alttext` attribute, with MediaWiki's `{\displaystyle …}` unwrapped on the way into the carrier. `display="block"` makes it a display carrier, emitted as its own `<p>` so it becomes its own markdown block and therefore its own unit. Sources 2 and 3 are left for the third slice, and the precedence order the design gives is what they slot into.

**Replace the outermost math wrapper**, walking up from the `<math>` node to the outermost ancestor whose class matches a known math container (`mwe-math-element`, `katex`, `MathJax`, `ltx_Math`). Prerendered KaTeX needs the same move for its own reason: `.katex` holds a MathML twin beside a `.katex-html` glyph-soup twin, and replacing only the former leaves the soup to extract as duplicate garbage.

**The call site** is the line before `trafilatura.extract` in `_extract_units_from_html`. `trafilatura.extract_metadata` keeps reading the original `html`, and `extract_article` keeps returning `page.html` unrewritten, so `images.py` probes the tree it probes today.

**Schemas** (`app/schemas/items.py`): `UNIT_TYPES` and `UnitType` gain `"formula"`; `FormulaUnit` with `display`, `spoken` and `latex`; `FormulaResponse`; both discriminated unions extended. `latex` rides on the persisted unit and is projected out of the wire shape the way `spoken` already is.

**Segmentation** (`extract.py`): `_split_units` gives a block that is exactly one display carrier the provisional type `"formula"`, and `units_from_markdown` constructs a `FormulaUnit` for it.

**Display**: a step beside `_normalize_display` rewrites surviving carriers into LaTeX delimiters, inline to `$…$` and display to `$$…$$`.

**Spoken**: inline carriers become `verbalize(tex)` inside `_to_spoken`, before the markdown-it walk, because a TeX body carries `_`, `^`, `\` and `{` that the walk would otherwise mangle. `sanitize_spoken` strips any carrier that survives anyway, the belt-and-suspenders role it already plays for leaked emphasis markers.

### Where this slice departs from the design's stage 4

The design's stage 4 gives a `FormulaUnit` the fixed interim placeholder `"Formula."`, the analogue of `"Code sample."`, replaced during enrichment. **That placeholder is an artifact of the design's stage ordering, not of the slicing.** Enrichment arrives a slice later, so shipping the placeholder here would ship a listener hearing the literal word "Formula." where they hear silence today, which is not the thing working.

So this slice floors a `FormulaUnit`'s spoken form straight to `verbalize(unit.latex)`, with `_FORMULA_FLOOR` when the verbalizer returns nothing usable. `verbalize` already exists here because inline math needs it. [[described-display-formulas]] then upgrades that spoken form to `Formula: <one sentence>` and demotes the verbalized LaTeX to the floor it was always designed to be.

### What the muster found the design does not cover

**Ordering inside `units_from_markdown`, which has one answer and the design does not give it.** Today the loop runs `display = _normalize_display(unit)` and then `said = _to_spoken(display)`. Stage 3 rewrites carriers into `$…$`; stage 4 needs the carriers still present when `_to_spoken` runs. Those two only coexist one way: `_normalize_display` first, the spoken form derived from its carrier-bearing result, and the carrier-to-LaTeX rewrite applied to that result afterwards to produce `display`. Settle it that way, or say in the answer why not.

**`_normalize_display` runs over carrier bodies, and nobody has checked what it does to them.** A TeX body can carry a backtick (LaTeX's opening quote), a `<` or a `>`. Confirm that `_CODE_SPAN`, `_LINK_DEST` and `_UNESCAPED_HTML_TAG` cannot reach inside a carrier; mask carriers first, the way code spans are already masked, if any of them can.

**The image containment probe: the design's hazard 1 is mislocated, and the fix it suggests does not apply.** It says a math-bearing unit "carries `$d_{k}$` where the tree holds a `<math>` subtree", which is the *display* form. `_find_anchors` probes `unit.spoken`, takes its first 25 characters, and only for the 25 longest units. No carrier ever reaches `spoken`, so "stripping carriers from the probe text" is a fix for a thing that cannot happen. The real exposure is narrower than stated: only a long paragraph whose **first 25 characters** contain math has its probe diverge from the tree's own text. Measure it on the arXiv fixture, and measure the thing that matters, which is whether `_find_container` still finds an element holding 80% of the anchors.

### Migration

**None. Settled at the muster, and CLAUDE.md was amended rather than worked around.**

`Item.units` is a `JSON` column, so a fourth union member is not a DDL change and there is nothing to write an `upgrade()` for; rows persisted before `formula` existed carry none of it and stay readable unchanged, so there is no backfill either. The recipe in CLAUDE.md used to read "a change to the item JSON needs a migration" flatly, which is unenforceable for a JSON column and would have been re-litigated by the next union member. It now says a migration is needed **when the persisted shape needs a backfill**, and states why a union member is exempt.

A no-op alembic revision was considered and rejected: it puts a revision that does nothing into a history whose whole job is replayable DDL, makes `alembic history` less informative rather than more, and becomes the precedent the next union member copies. Invariant 7, "a schema change is a migration", is untouched and still holds: this is not a schema change.

### Fixtures

One per family this slice covers, per CLAUDE.md's rule, with cases in `test_extract.py`:

- **MathML inline**, arXiv HTML / LaTeXML: the broken sentence is the case. It must read "While for small values of d sub k the two mechanisms perform similarly".
- **MathML display**, Wikipedia / MediaWiki: the a11y-wrapper case, which is what proves the outermost-wrapper rule rather than the `<math>` node.
- **Prerendered KaTeX**: the MathML twin beside the `.katex-html` glyph soup, which is what proves the soup does not extract as duplicate garbage.

### Done when

The arXiv sentence is whole again, Wikipedia's dangling colon is followed by the spoken Pythagorean equation, no carrier appears in any `display` or `spoken` value, the image container is still found on the arXiv fixture, and `uv run pytest` / `uv run ruff check` / `uv run ty check` are green in `api/`.

**And it has been played.** One recovered display formula and one inline formula, listened to, before this is called done.

---

Related: [[quest-log/README|the quest log]] · [[formulas-read-aloud]] · [[latex-formulas-not-read]]
