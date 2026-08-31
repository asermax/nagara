---
title: "Described display formulas"
tags:
  - quest
summary: "Second slice: describe display formulas on the shared describe budget, with the verbalized LaTeX demoted to the floor."
status: open
kind: build
adventure: formulas-read-aloud
blocked_by:
  - mathml-recovered-and-spoken
priority: 2-soon
created: "2026-08-30"
---

# Described display formulas

## What

Upgrade a display formula's spoken form from the verbalized LaTeX to `Formula: <one sentence>`, on the describer's existing budget, concurrency, floor and degradation machinery. The verbalized LaTeX stops being the answer and becomes the floor, which is where the design always meant it to sit. Silence is never a rung on the ladder.

This slice touches `describe.py` and nothing in extraction. It is independent of [[raw-math-delimiters]]; both wait only on [[mathml-recovered-and-spoken]] for the `FormulaUnit` to exist.

## Design

The shape is settled on [[latex-formulas-not-read]], stage 5. What follows is what this slice takes from it and what the muster added.

### What this slice builds

In `app/service/describe.py`:

- `_FORMULA_FLOOR = "Formula with no description."`
- `build_formula_prompt(title: str | None, intro: str | None, latex: str) -> str`, and its template, following the code prompt's discipline: exactly one sentence naming what the formula is and what it is for, the introducing paragraph as the authority, no opener, and no reading the symbols aloud, since the floor below already does that.
- `enrich_with_descriptions` gains a third branch in the job walk: `elif isinstance(unit, FormulaUnit): jobs.append((i, "formula"))`.
- `describe_one` gains the formula branch's `contents`: `build_formula_prompt(title, result[index - 1].spoken if index > 0 else None, result[index].latex)`. There is **no `_code_content` analogue to write**: `latex` rides on the unit precisely so the describer does not re-derive the TeX out of `display`.

Everything downstream generalizes already and needs no change: the single `max_describes` budget counted in document order, the `asyncio.Semaphore`, `asyncio.gather(return_exceptions=True)` so one failure never discards the rest, the prefix on success (`Formula: `), and `on_describe("formula")` so the ledger meters it by kind.

`record_describer_cost`'s docstring says `kind` is the describable's type, `code` or `image`. Add `formula` to it.

### The floor ladder

| Outcome | Spoken form | Degradation |
|---|---|---|
| Described | `Formula: <one sentence>` | none |
| Past the cap | `verbalize(unit.latex)` | `{"type": "formula", "reason": "describe cap reached"}` |
| Describe failed | `verbalize(unit.latex)` | `{"type": "formula", "reason": "describe failed"}` |
| Verbalizer returns nothing usable | `_FORMULA_FLOOR` | as above |

**A formula-only outage does not raise.** The existing `code_within_cap > 0 and code_resolved == 0` guard stays exactly as it is and gains no formula equivalent. Code raises because a code unit's floor is an honest admission that says nothing; a formula's floor is the verbalized LaTeX, a real spoken form carrying the actual content. Formula follows the image rule: it degrades, it never fails the item.

### Formulas join a budget that is already contended

A `FormulaUnit` draws on the same single `max_describes` cap as code and images, counted in document order, which is what the design intends and what makes the combined total honest. It also means a formula-dense article spends budget that code blocks after it would otherwise have had.

That contention, and the fact that the code-outage guard does not fire when a kind is starved by the cap rather than by failures, is **pre-existing behaviour of shipped code** and is not this raid's to settle. It is logged loose as `describe-budget-starves-later-kinds` (named, not linked: it belongs to no effort and outlives this one). Do not fix it here; do not add a formula equivalent of the code guard either way.

### The design's hazard 3 is right for the wrong reason

It says "137 formulas against `describe_max_per_item` means most of that article floors to `verbalize`". The 137 are **inline** carriers. Inline math never becomes a unit and never reaches the describer at all: it is verbalized in place, unconditionally, on every article. So the verbalizer is load-bearing on arXiv not because the cap is spent but **by construction**, and the conclusion the hazard draws is stronger than the reason it gives. Nothing in this slice changes because of it, but do not go looking for 137 formula units that do not exist.

### Done when

A display formula on the Wikipedia fixture reads `Formula: <sentence>`; the cost ledger carries a `{"kind": "formula"}` row for it; a forced describe failure floors to the verbalized LaTeX and the item still reaches `ready`; an item whose only describables are formulas and whose every describe fails does **not** raise; and `uv run pytest` / `uv run ruff check` / `uv run ty check` are green in `api/`.

**And it has been played.** A described display formula, listened to, so a leaked marker inside the model's string value is caught the only way it ever is.

---

Related: [[quest-log/README|the quest log]] · [[formulas-read-aloud]] · [[latex-formulas-not-read]] · [[mathml-recovered-and-spoken]]
