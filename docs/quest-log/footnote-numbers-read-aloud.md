---
title: "Footnote numbers read aloud"
tags:
  - quest
summary: "Footnote reference markers survive extraction and get spoken; strip them once the note content is extracted."
status: solved
kind: build
adventure:
blocked_by: []
priority: 1-now
created: "2026-08-30"
---

# Footnote numbers read aloud

## What

Footnote markers stay in the extracted text and get spoken by TTS. Should be stripped after extracting the note content.

## Design

A footnote *reference* marker is removed structurally, at the HTML, before the single `trafilatura.extract` call ever runs. The footnote *body* stays: it extracts as a list item at the end of the article and reads as a real sentence.

### Why not a text-level strip

The shape our own corpus produces has no text-level discriminator. `api/tests/fixtures/my-ai-adoption-journey.html` uses GitHub-flavored footnotes (`<sup><a data-footnote-ref>1</a></sup>`), and trafilatura renders them as a bare digit floating in prose:

```
"...invoke external behavior in a loop 1 At a bare minimum..."
"...if AI is here to stay 3, I'm a software craftsman..."
```

The same article legitimately says "phase 1 and 2" and "step 5, I'm also operating". `stay 3, I'm a software craftsman` and `step 5, I'm also operating` are the same shape as text. A regex that removes one removes the other.

The markup separates them exactly, so the strip goes where the markup still exists.

### What changes

`_extract_units_from_html` in `api/app/service/extract.py` passes a new module constant to its existing `trafilatura.extract` call:

```python
_FOOTNOTE_REF_XPATH = [
    "//sup[a]",
    "//a[@data-footnote-ref]",
    "//sup[@class='reference']",
    "//a[contains(@class, 'footnote-anchor')]",
]
```

Four rows, each an unambiguous reference-marker shape: a superscript wrapping a link (GitHub, pandoc, kramdown, most static-site generators), an explicit `data-footnote-ref`, Wikipedia's `sup.reference`, and Substack's `a.footnote-anchor`. Bare `//sup` is deliberately not in the list: a superscript with no link is an exponent, an ordinal, or a trademark as often as it is a footnote.

This is the only call site, so both the plain fetch and the firecrawl fallback are covered by construction (invariant 1 and invariant 5 hold unchanged: one extraction, and the pruning rides on it rather than adding a pass).

The marker leaves `display` as well as `spoken`. That is correct here rather than a compromise: trafilatura drops the footnote section's anchors, so a surviving `[1]` in the display markdown is a reference pointing at nothing.

`_FOOTNOTE_GLYPHS` is untouched. It strips the `↩`/`⇧` backref off the footnote bodies and is a separate rule from this one.

### What this does not cover

Naming the gap so the rule is not mistaken for complete:

- **A literal `[1]` written as text**, with no footnote markup around it, is untouched.
- **A bare digit with no markup** is untouched, and is unrecoverable at the text layer for the reason above.

That gap is the case for a residual text-level strip, and it is a follow-up quest rather than part of this one.

### Recorded, not implemented

The residual layer's two calls are settled, so whoever adds it does not re-litigate them. Neither is built here:

- **A bracketed-text strip caps at one to three digits.** `[1]`, `[12]`, `[123]` and runs like `[1][2]` strip; `[1997]` does not, because four digits is a year or a figure number.
- **Unicode superscripts (`¹²³`) are left alone.** They read as unambiguous and are not: `m⁻¹`, `x²` and `km h⁻¹` are prose-meaningful in scientific writing. Structural pruning leaves them alone anyway, so this costs nothing now.

### Coverage

- `api/tests/fixtures/footnote-markers.html`, a new fixture carrying every marker shape the xpath list claims, each in a sentence, plus the near-misses that must survive: prose numbers, a bracketed aside, a citation, a bracketed year, an array index in prose and in a code block, and a superscript exponent.
- A real-artifact assertion against `my-ai-adoption-journey.html`: the four leaked markers gone, `"phase 1 and 2"` and `"step 5"` intact, the four footnote bodies still present.
- `hostile.md` is left alone; its `len == 6` assertion is the pinned probe from experiment 002.

### Documentation

- `docs/product-design/what-gets-read-aloud.md` claims footnote markers are already dropped, which is false. The corrected sentence says which markers are dropped (the ones the markup identifies) and which are not, rather than swapping one overclaim for another.
- `docs/technical-design/article-extraction.md` gains the rule in "Dropping a unit, and marker-aware cleanup", including the existing `↩`/`⇧` strip it never documented.


## Answer

Built. `_FOOTNOTE_REF_XPATH` is handed to the single `trafilatura.extract` call in `_extract_units_from_html` as `prune_xpath`, removing footnote reference markers from the tree before extraction runs. Four expressions: `//sup[a]`, `//a[@data-footnote-ref]`, `//sup[@class='reference']`, `//a[contains(@class, 'footnote-anchor')]`.

**How far it reaches.** Every marker shape probed reaches the markdown as something a text rule cannot safely touch, and all four are now gone at the source. Verified on two artifacts: the synthetic `footnote-markers.html`, which carries one paragraph per shape, and the real corpus article `my-ai-adoption-journey.html`, whose four leaked markers (`"in a loop 1"`, `"time savings 2"`, `"here to stay 3"`, `"in the game here 4"`) are gone while `"phase 1 and 2"` and `"step 5"` survive and the four footnote bodies still read. Extraction is byte-identical on the other three HTML fixtures, so the blast radius is the two articles that have footnotes at all.

**Heard, not just tested.** espeak-ng phonemization of the affected sentence gives `In a# l'u:p w'Vn at#@ b'e@ m'InIm@m` before and `In a# l'u:p at#@ b'e@ m'InIm@m` after: the marker was being spoken as the word "one". The kept-numbers sentence still gives `f'eIz w'Vn ... t'u:` and `st'Ep f'aIv`. Local Kokoro synthesis was not reachable (the `en_core_web_sm` spacy model would not download in this environment), so the engine that phonemized is not the production one; the question it answers, whether a stray digit becomes a spoken word, is engine-independent.

**What would make it stop being true.** A publisher whose footnote markup is none of the four shapes: a superscript with the anchor outside it, a marker built from a `<span>`, or a class name nobody has seen. That fails open, leaving a marker to be read aloud rather than eating prose, which is the right direction to fail in. A trafilatura release that stops honouring `prune_xpath`, or that starts inlining footnote text at the reference site, would also break it, and the two fixture tests are what catch either.

**Left behind.** `api/tests/fixtures/footnote-markers.html`, the synthetic probe carrying every claimed shape and the near-misses that must survive. The gap this does not cover is logged as [[literal-footnote-markers]].

---

Related: [[quest-log/README|the quest log]] · [[article-extraction]] · [[what-gets-read-aloud]]
