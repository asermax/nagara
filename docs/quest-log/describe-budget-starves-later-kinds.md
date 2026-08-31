---
title: "Describe budget starves later kinds"
tags:
  - quest
summary: "One shared describe cap counted in document order lets an early kind spend the whole budget, and the code-outage guard does not fire when it happens."
status: open
kind: design
adventure:
blocked_by: []
priority: 2-soon
created: "2026-08-30"
---

# Describe budget starves later kinds

## What

`enrich_with_descriptions` runs **one** describe budget across every describable kind, counted in document order. A kind that appears early and often can spend the whole cap, leaving every later describable floored. That is defensible on its own. What is not is the second half: **the guard that exists to catch a silent code outage does not fire in exactly this case**, so an item whose every code block floored reaches `ready` with no error and no signal beyond the degradation list.

This is about shipped code and it is true today, before any new unit kind is added. It is logged loose, with no adventure, because it outlives whatever effort surfaced it.

## Design

### The mechanism, as it stands in `api/app/service/describe.py`

`enrich_with_descriptions` walks the unit list once and builds a flat `jobs` list in document order: a `CodeUnit` contributes `(i, "code")`, an index the image precedence flagged contributes `(i, "image")`. It then splits on the cap:

- `within_cap = jobs[:max_describes]`
- `beyond_cap = jobs[max_describes:]`

`max_describes` is `settings.describe_max_per_item`, whose default is **25** (`api/app/config.py`). Everything in `beyond_cap` degrades without a call: a code unit floors to `"Code with no description."`, an image keeps whatever its precedence fallback already put on `spoken`, and each records `{"reason": "describe cap reached"}`.

Because the list is in **document order** and the cap is a **prefix**, position decides who gets described. Nothing balances across kinds and nothing reserves a share for a kind that appears late.

### Where the guard fails

The outage guard is the last thing the function does:

```python
code_within_cap = sum(1 for _, kind in within_cap if kind == "code")
...
if code_within_cap > 0 and code_resolved == 0:
    raise RuntimeError("describe: every code unit failed")
```

Its own docstring states the intent: "a code-bearing item with zero code descriptions is a silent total failure, so that is an outage the item fails on."

The starvation case produces **exactly that outcome** and the guard does not fire, because it counts failures inside the cap rather than code units in the item. When every code job lands in `beyond_cap`, `code_within_cap` is `0`, the first conjunct is false, and the raise is skipped. The item has zero code descriptions, every code block reads the floor, and it reaches `ready`.

So the guard catches a describer outage and misses a budget outage, though the two are indistinguishable to a listener.

### The concrete case, with today's two kinds

An article carrying 25 or more describable images before its first code block. The images fill the cap in document order, every code block falls past it, all of them floor, and nothing raises. The image path is unharmed by design (an over-budget image degrades through its precedence, never drops), so the whole cost lands on code, which is the kind whose floor says nothing.

The exposure grows with every kind added to the shared budget. The `formulas-read-aloud` raid adds a third: on one measured article (lilianweng) 24 display formulas meet a cap of 25. Named rather than linked, because that effort's records are struck when it ends and this quest outlives them.

### What this settles

Four options, and picking between them is the work:

1. **Leave the budget, widen the guard.** Change the first conjunct to count code units in the item rather than in the cap, which is the smallest change and the one that matches the docstring's stated intent. It fails items that reach `ready` today, so it is a real behaviour change and needs the call made deliberately.
2. **Leave both, and make the starvation visible instead.** The degradation list already records `describe cap reached` with a `type`; the cost ledger already meters by kind. Decide that an operator reading those is the intended signal and write that down, so the gap between the guard and its docstring stops reading as a bug.
3. **Reserve per kind.** Split the single cap into a per-kind share so no kind can starve another. Costs the "one combined per-item cap" property the config comment currently claims.
4. **Raise the cap.** Cheapest, settles nothing: it moves the article that triggers it rather than removing the shape.

Whichever way it goes, `enrich_with_descriptions`'s docstring and the `describe_max_per_item` config comment both describe the current behaviour as a single combined budget and neither mentions starvation. They get fixed with it.

**No note is written by this quest.** The explanation belongs in [[the-describer]] once the behaviour is settled, per the vault charter's rule that a note describes something that exists.

---

Related: [[quest-log/README|the quest log]] · [[the-describer]]
