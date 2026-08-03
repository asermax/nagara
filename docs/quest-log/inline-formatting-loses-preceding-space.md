---
title: "Inline formatting loses its preceding space"
tags:
  - quest
summary: "Links and other inline-formatted runs lose the space separating them from the text before them, corrupting both spoken audio and rendered read-along text."
status: solved
kind: build
adventure: richer-extraction
blocked_by: []
priority: 1-now
created: "2026-07-17"
---

# Inline formatting loses its preceding space

## What

Links and other inline-formatted runs lose the space that should separate them from the text immediately before them: a source like `click here<a href=…>link</a>` extracts and renders as `click herelink` instead of `click here link`. This corrupts both the spoken audio (the words run together) and the rendered read-along text, in [[article-extraction]]'s display/spoken split.

Observed during real dogfood use through Tachikoma, distinct from the markdown-faithfulness question of whether formatting is captured at all: this is a plain word-boundary bug in extraction or normalization.

**Diagnosed and designed 2026-08-02** inside [[richer-extraction]], which measured the cause and settled the fix. It stays a standalone quest because it touches no contract and can ship on its own schedule, which is why it carries no blockers.

## Design

### The cause is not what this quest assumed

It is neither an emphasis defect nor a markdown-rendering one. **trafilatura discards the whitespace following an inline element**, in every output format, and the loss happens in its DOM handling upstream of any renderer.

The source HTML has the space and lxml sees it. `<strong>install Python</strong> on Windows` carries a tail of `' on Windows'`, and trafilatura's markdown emits `install Pythonon Windows`. So does its XML.

> [!important] This refutes the escape route that looked obvious
> `include_formatting=False` cannot help, and neither can switching output format, because the whitespace is gone before the format is chosen. There is nothing to escape to.

### What it actually costs

Counting every inline element whose tail begins with a space, then checking whether trafilatura kept the boundary:

| Article | Spaced inline elements | Space lost | Reaches audio |
|---|---:|---:|---:|
| realpython | 230 | 24 | 3 |
| mitchellh | 10 | 5 | 1 |
| acx, newyorker, wired, simonwillison | 34 | 0 | 0 |
| **total** | **274** | **29** | **4** |

The existing repairs catch 25 of 29. The four reaching a listener are `realpart`, `imaginarypart`, `Noneand` and `AGENTS.md(or`, every one an inline-code or link boundary and never emphasis. The repairs are sufficient for what they target; the residual is a neighbouring class they were never written for.

Two related worries dissolve on measurement. The lossy belt-and-suspenders marker strip in `_to_spoken` is **not** silently degrading audio: it fires rarely and where it does the result is correct. And the intentional non-repairs documented in `extract.py`, the unspaced `2*3*4` run and the unbalanced `***`, do not occur anywhere in the corpus.

### The fix

**Extend `_normalize_display` to inline code spans and link destinations**, alongside the emphasis pair it already handles. Same function, same shape, no new mechanism.

Verified over the corpus: 40 units change, zero regressions, and fusions reaching audio drop from 4 to 2.

> [!warning] The obvious regex is wrong and this already cost one rewrite
> Anchoring on a backtick pair and testing the character after it makes the *closing* backtick of a non-matching span become the opener of the next match, so the gap between two spans is treated as a span and the space lands inside it. Capture the following character in a lookahead instead, exactly as `_EMPHASIS` already does, so every span is consumed in document order.

`prototype_boundary_repair.py` on `idea/firecrawl-markdown-fidelity` carries the working regexes and seven cases, including the three that must be left alone.

### The two survivors are a table problem

Inside a table cell trafilatura drops the inline markup **along with** the space, so `<strong>real</strong> part` becomes `realpart` with no delimiter left to key on. A listener hears "a realpart and animaginarypart". Nothing at the markdown layer can fix it, because the information is gone before extraction hands it over.

That belongs with the open question of whether a table deserves its own unit variant. [[typed-unit-contract]] folds tables into `paragraph` and gives them no discriminator, so what is left is a product question rather than a contract one.

### How it is verified

Seam 2, the pure segmentation functions. Per `CLAUDE.md` this is an extraction rule, so it owes a function in `extract.py`, a case in `test_extract.py`, a fixture, and a callout in [[article-extraction]].

The fix changes what a listener hears, so it is one of the inputs to [[richer-extraction-listen-pass]].

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[richer-extraction]] · [[typed-unit-contract]]
